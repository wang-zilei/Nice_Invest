"""
graph.py — LangGraph 编排图
实现 Router → 并行 Agent → Summary → (可选) 评判 Agent 的完整分析流程。

核心架构：
  用户输入 → Router(路由判断) → 并行4个Agent(基本面/技术面/估值/新闻) → Summary(汇总) → 输出
  评判模式: Summary后调用评判Agent进行多模型对比打分
"""
from typing import Literal, List, Dict
from langgraph.graph import StateGraph, END
from langgraph.types import Send
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import json
import os
import traceback

from src.state import AnalysisState
from src.mcp_tools.tushare_api import get_stock_basic

try:
    from config import DEFAULT_MODEL
except ImportError:
    DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "deepseek-chat")


# ============================================================
# LLM 工厂 —— 统一使用 OpenAI 兼容协议
# ============================================================
LLM_TIMEOUT = 60  # 单次 LLM 请求超时（秒）
AGENT_TIMEOUT = 180  # 单个 Agent 整体执行超时（秒）


def get_llm(model: str = None):
    """根据模型名称创建 LLM 实例（OpenAI 兼容协议）

    优先读取 os.environ（由 server.py _apply_llm_config 动态设置），
    回退到 config.py 静态值。这确保用户自备 Key / 体验 Key 能正确注入。
    """
    try:
        from config import (
            OPENAI_API_KEY as _CFG_OPENAI_KEY, OPENAI_BASE_URL as _CFG_OPENAI_URL,
            DEEPSEEK_API_KEY as _CFG_DEEPSEEK_KEY, DEEPSEEK_BASE_URL as _CFG_DEEPSEEK_URL,
            QWEN_API_KEY as _CFG_QWEN_KEY, QWEN_BASE_URL as _CFG_QWEN_URL,
        )
    except ImportError:
        _CFG_OPENAI_KEY = _CFG_OPENAI_URL = ""
        _CFG_DEEPSEEK_KEY = _CFG_DEEPSEEK_URL = ""
        _CFG_QWEN_KEY = _CFG_QWEN_URL = ""

    # 优先从环境变量读取（server.py _apply_llm_config 会动态设置）
    openai_key = os.environ.get("OPENAI_API_KEY", "") or _CFG_OPENAI_KEY
    openai_url = os.environ.get("OPENAI_BASE_URL", "") or _CFG_OPENAI_URL
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "") or _CFG_DEEPSEEK_KEY
    deepseek_url = os.environ.get("DEEPSEEK_BASE_URL", "") or _CFG_DEEPSEEK_URL
    qwen_key = os.environ.get("QWEN_API_KEY", "") or _CFG_QWEN_KEY
    qwen_url = os.environ.get("QWEN_BASE_URL", "") or _CFG_QWEN_URL
    model = model or os.environ.get("DEFAULT_MODEL", "") or DEFAULT_MODEL

    common = {
        "temperature": 0.3,
        "request_timeout": LLM_TIMEOUT,
        "max_retries": 2,
    }

    if model == "gpt-4o":
        return ChatOpenAI(model="gpt-4o", api_key=openai_key, base_url=openai_url, **common)
    elif model.startswith("deepseek"):
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=deepseek_key,
            base_url=deepseek_url,
            **common,
        )
    elif model == "qwen-plus":
        return ChatOpenAI(model="qwen-plus", api_key=qwen_key, base_url=qwen_url, **common)
    else:
        # 兜底：优先用 openai_key，回退到 deepseek_key
        return ChatOpenAI(
            model=model,
            api_key=openai_key or deepseek_key,
            base_url=openai_url or deepseek_url,
            **common,
        )


# ============================================================
# Agent 定义
# ============================================================
def get_agent_llm(agent_type: str):
    """为不同类型的 Agent 创建 LLM 实例，使用用户选择的模型"""
    llm = get_llm()
    if agent_type == "fundamental":
        from src.agents.analyst import create_fundamental_agent
        return create_fundamental_agent(llm)
    elif agent_type == "technical":
        from src.agents.technical import create_technical_agent
        return create_technical_agent(llm)
    elif agent_type == "valuation":
        from src.agents.valuation import create_valuation_agent
        return create_valuation_agent(llm)
    elif agent_type == "news":
        from src.agents.news import create_news_agent
        return create_news_agent(llm)
    elif agent_type == "summary":
        from src.agents.summary import create_summary_agent
        return create_summary_agent(llm)


# ============================================================
# Router 节点 —— 路由判断 + 数据预处理
# ============================================================
def router_node(state: AnalysisState) -> AnalysisState:
    """
    Router: 判断分析类型，预处理股票代码
    - 将中文股票名称转为 ts_code
    - 确定要执行的 Agent 列表
    """
    stock_code = state.get("stock_code", "")
    analysis_type = state.get("analysis_type", "full")

    # 如果输入不是标准 ts_code 格式，尝试搜索
    if "." not in stock_code and len(stock_code) <= 6:
        try:
            result = get_stock_basic(stock_code + ".SH")
            if "未找到" not in result:
                stock_code = stock_code + ".SH"
            else:
                result_sz = get_stock_basic(stock_code + ".SZ")
                if "未找到" not in result_sz:
                    stock_code = stock_code + ".SZ"
        except Exception:
            pass
    elif "." not in stock_code and len(stock_code) > 6:
        # 中文名称，需要搜索（简化处理：提示用户使用代码）
        pass

    # 确定要执行的 Agent
    agent_map = {
        "full": ["fundamental", "technical", "valuation", "news"],
        "fundamental": ["fundamental"],
        "technical": ["technical"],
        "valuation": ["valuation"],
        "news": ["news"],
    }
    agents_to_run = agent_map.get(analysis_type, agent_map["full"])

    return {
        **state,
        "stock_code": stock_code,
        "agent_results": [],
        "messages": state.get("messages", []) + [
            HumanMessage(content=f"开始分析股票 {stock_code}，执行 Agent: {', '.join(agents_to_run)}")
        ]
    }


# ============================================================
# Agent 执行节点 —— ReAct 循环
# ============================================================
from langchain_core.messages import ToolMessage

def run_agent_react(agent_type: str, state: AnalysisState) -> str:
    """
    执行单个 Agent 的 ReAct 循环
    流程: LLM 判断 → 调用工具 → 获取结果 → 再次判断 → 直到 LLM 认为分析完成
    最大迭代次数限制防止无限循环，每个 LLM 调用有超时保护。
    """
    import concurrent.futures
    import threading

    def _execute():
        agent = get_agent_llm(agent_type)
        stock_code = state.get("stock_code", "")

        if agent_type == "summary":
            results = state.get("agent_results", [])
            parts = []
            for r in results:
                parts.append(f"【{r['agent_name']}】（置信度: {r['confidence']}）\n{r['analysis']}")
            combined = "\n\n---\n\n".join(parts)
            messages = [HumanMessage(content=f"""请汇总以下四个维度的分析结果，输出综合投资报告。

各 Agent 分析结果：
{combined}

请先调用 cross_validate_agents 检查关键结论之间的交叉一致性，然后调用 calculate_weighted_score 计算综合评分，最后按五段式模板输出完整报告。""")]
        else:
            messages = [HumanMessage(content=f"请分析股票 {stock_code} 的{agent_type}面情况，调用所需工具后给出完整分析报告。")]

        max_steps = 12  # 充足步数，防止复杂分析被截断
        step = 0

        while step < max_steps:
            step += 1
            try:
                response = agent.invoke({"messages": messages})
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    raise RuntimeError(f"[{agent_type}] LLM 请求超时（{LLM_TIMEOUT}秒），请检查 API 连接或网络状态")
                # 翻译常见 API 错误
                if "402" in error_msg or "Insufficient Balance" in error_msg:
                    raise RuntimeError(f"[{agent_type}] API 账户余额不足（402）。请检查 API Key 余额或配置自己的 Key")
                if "401" in error_msg or "Unauthorized" in error_msg:
                    raise RuntimeError(f"[{agent_type}] API Key 无效（401），请检查 Key 是否正确或已过期")
                if "403" in error_msg or "Forbidden" in error_msg:
                    raise RuntimeError(f"[{agent_type}] API 访问被拒绝（403），请检查账户权限")
                if "429" in error_msg or "Rate" in error_msg:
                    raise RuntimeError(f"[{agent_type}] API 请求频率过高（429），请稍后重试")
                raise RuntimeError(f"[{agent_type}] LLM 调用失败: {error_msg}")

            has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls

            if not has_tool_calls:
                content = response.content if hasattr(response, 'content') else str(response)
                return content

            ai_msg = AIMessage(
                content=response.content if hasattr(response, 'content') else "",
                tool_calls=response.tool_calls,
            )
            if hasattr(response, 'id') and response.id:
                ai_msg.id = response.id
            messages.append(ai_msg)

            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call.get("id", "")

                if agent_type == "fundamental":
                    from src.agents.analyst import FUNDAMENTAL_TOOLS
                    tools = FUNDAMENTAL_TOOLS
                elif agent_type == "technical":
                    from src.agents.technical import TECHNICAL_TOOLS
                    tools = TECHNICAL_TOOLS
                elif agent_type == "valuation":
                    from src.agents.valuation import VALUATION_TOOLS
                    tools = VALUATION_TOOLS
                elif agent_type == "news":
                    from src.agents.news import NEWS_TOOLS
                    tools = NEWS_TOOLS
                elif agent_type == "summary":
                    from src.agents.summary import SUMMARY_TOOLS
                    tools = SUMMARY_TOOLS
                else:
                    tools = []

                tool_obj = next((t for t in tools if t.name == tool_name), None)
                if tool_obj:
                    try:
                        result = tool_obj.invoke(tool_args)
                        messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))
                    except Exception as e:
                        messages.append(ToolMessage(content=f"工具调用失败: {str(e)}", tool_call_id=tool_call_id))
                else:
                    messages.append(ToolMessage(content=f"未找到工具: {tool_name}", tool_call_id=tool_call_id))

        last_msg = messages[-1] if messages else AIMessage(content="分析超时")
        return last_msg.content if hasattr(last_msg, 'content') else str(last_msg)

    # 用线程池执行 + 整体超时兜底
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_execute)
        try:
            return future.result(timeout=AGENT_TIMEOUT)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(
                f"[{agent_type}] Agent 执行超时（{AGENT_TIMEOUT}秒），"
                f"请检查 API Key 是否正确配置、网络是否可达"
            )


# ============================================================
# Summary 节点 —— ReAct 汇总（升级版）
# ============================================================
def summary_node(state: AnalysisState) -> AnalysisState:
    """
    Summary Agent (ReAct 模式): 带工具的综合汇总
    - 交叉验证各 Agent 结论一致性（cross_validate_agents）
    - 核实关键指标数据一致性（verify_data_consistency）
    - 加权综合评分（calculate_weighted_score）
    - 输出五段式综合投资报告
    """
    stock_code = state.get("stock_code", "")
    agent_results = state.get("agent_results", [])

    if not agent_results:
        return {
            "summary": "无分析结果可汇总",
            "final_verdict": "数据不足",
        }

    # 使用 ReAct 循环执行汇总分析
    try:
        summary_text = run_agent_react("summary", state)
    except Exception as e:
        # 降级：简单拼接各 Agent 结果
        parts = []
        for r in agent_results:
            parts.append(f"【{r['agent_name']}】\n{r['analysis']}")
        summary_text = f"## 分析结果汇总（ReAct 执行异常，降级为简单拼接）\n\n异常信息: {str(e)}\n\n" + "\n\n---\n\n".join(parts)

    # 从摘要中判断投资倾向
    verdict = "中性"
    if any(kw in summary_text for kw in ["强烈看好", "增持", "强烈推荐"]):
        verdict = "看好"
    elif any(kw in summary_text for kw in ["强烈看空", "减持", "建议回避"]):
        verdict = "看空"
    elif "看好" in summary_text:
        verdict = "看好"
    elif "看空" in summary_text:
        verdict = "看空"

    return {
        "summary": summary_text,
        "final_verdict": verdict,
    }


# ============================================================
# 评判 Agent 节点 —— 多模型对比评测
# ============================================================
def evaluation_node(state: AnalysisState) -> AnalysisState:
    """
    评判 Agent: 独立于分析链路，对多模型的输出进行对比打分
    - 使用固定 LLM 作为裁判（通常用 gpt-4o）
    - 4 维度打分：幻觉检测、推理质量、风险敏感度、工具调用准确率
    - 输出雷达图对比报告
    """
    eval_models = state.get("eval_models", ["gpt-4o"])
    agent_results = state.get("agent_results", [])
    stock_code = state.get("stock_code", "")

    # 获取原始真实数据（用于幻觉检测对照）
    try:
        raw_data = get_stock_basic(stock_code)
    except Exception:
        raw_data = "无法获取原始数据"

    evaluation_results = []

    # 对每个模型进行评测
    for model in eval_models:
        # 构建评判 prompt
        eval_prompt = f"""作为独立的评判 Agent，请对以下股票分析结果进行多维度评估。

【原始真实数据】（来自 Tushare Pro）
{raw_data}

【模型分析输出】
{chr(10).join([f"{r['agent_name']}: {r['analysis']}" for r in agent_results])}

请从以下 4 个维度打分（0~10分）：

1. **幻觉检测**（事实一致性）：分析中的事实/数值是否与原始数据一致？是否存在捏造数据？
2. **推理质量**（逻辑完整性）：分析逻辑是否严密？结论是否有数据支撑？
3. **风险敏感度**（风险识别）：是否识别到关键风险因素？风险提示是否充分？
4. **工具调用准确率**（工具使用）：工具选择是否合理？调用参数是否正确？

请按以下 JSON 格式输出（只需 JSON，不要其他内容）：
{{"hallucination_score": 0-10, "reasoning_score": 0-10, "risk_sensitivity": 0-10, "tool_accuracy": 0-10}}"""

        eval_llm = get_llm(model)
        response = eval_llm.invoke([HumanMessage(content=eval_prompt)])
        content = response.content

        # 解析 JSON 结果
        try:
            # 提取 JSON 部分
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                scores = json.loads(content[start:end])
                result = {
                    "model": model,
                    "hallucination_score": scores.get("hallucination_score", 0),
                    "reasoning_score": scores.get("reasoning_score", 0),
                    "risk_sensitivity": scores.get("risk_sensitivity", 0),
                    "tool_accuracy": scores.get("tool_accuracy", 0),
                    "overall_score": round(
                        (scores.get("hallucination_score", 0) +
                         scores.get("reasoning_score", 0) +
                         scores.get("risk_sensitivity", 0) +
                         scores.get("tool_accuracy", 0)) / 4, 1
                    )
                }
                evaluation_results.append(result)
            else:
                evaluation_results.append({
                    "model": model, "hallucination_score": 0, "reasoning_score": 0,
                    "risk_sensitivity": 0, "tool_accuracy": 0, "overall_score": 0
                })
        except json.JSONDecodeError:
            evaluation_results.append({
                "model": model, "hallucination_score": 0, "reasoning_score": 0,
                "risk_sensitivity": 0, "tool_accuracy": 0, "overall_score": 0,
                "raw_response": content
            })

    return {
        "evaluation_results": evaluation_results,
    }


# ============================================================
# 构建图 —— LangGraph StateGraph
# ============================================================
def build_graph():
    """
    构建 LangGraph 工作流图
    流程: router → [agents:parallel] → summary → (evaluation if eval_mode) → end
    """
    workflow = StateGraph(AnalysisState)

    # 注册节点
    workflow.add_node("router", router_node)
    workflow.add_node("fundamental", lambda s: _run_agent("fundamental", s))
    workflow.add_node("technical", lambda s: _run_agent("technical", s))
    workflow.add_node("valuation", lambda s: _run_agent("valuation", s))
    workflow.add_node("news", lambda s: _run_agent("news", s))
    workflow.add_node("summary", summary_node)
    workflow.add_node("evaluation", evaluation_node)

    # 入口
    workflow.set_entry_point("router")

    # 条件边：根据分析类型路由到对应 Agent（Send 支持并行）
    workflow.add_conditional_edges(
        "router",
        lambda s: _route_agents(s),
        {
            "fundamental": "fundamental",
            "technical": "technical",
            "valuation": "valuation",
            "news": "news",
        }
    )

    # Agent → Summary
    for agent in ["fundamental", "technical", "valuation", "news"]:
        workflow.add_edge(agent, "summary")

    # Summary → (Evaluation or End)
    workflow.add_conditional_edges(
        "summary",
        lambda s: "evaluation" if s.get("eval_mode", False) else "end",
        {"evaluation": "evaluation", "end": END}
    )

    workflow.add_edge("evaluation", END)

    return workflow.compile()


def _run_agent(agent_type: str, state: AnalysisState) -> AnalysisState:
    """Agent 执行节点的包装器"""
    stock_code = state.get("stock_code", "")
    analysis = run_agent_react(agent_type, state)

    # 解析置信度（简单从文本中提取）
    confidence = 0.8  # 默认值
    if any(kw in analysis for kw in ["数据充分", "信息完整", "指标清晰"]):
        confidence = 0.85
    elif any(kw in analysis for kw in ["数据不足", "信息有限", "缺乏"]):
        confidence = 0.65

    agent_name_map = {
        "fundamental": "基本面",
        "technical": "技术面",
        "valuation": "估值",
        "news": "新闻舆情"
    }

    result = {
        "agent_name": agent_name_map.get(agent_type, agent_type),
        "analysis": analysis,
        "confidence": confidence,
        "data_sources": ["Tushare Pro"]
    }

    return {
        "agent_results": [result],
        "messages": [
            AIMessage(content=f"{agent_name_map.get(agent_type, agent_type)}分析完成")
        ]
    }


def _route_agents(state: AnalysisState) -> list:
    """路由决策：返回 Send 列表，支持单/多 Agent 并行执行"""
    analysis_type = state.get("analysis_type", "full")
    agent_map = {
        "full": ["fundamental", "technical", "valuation", "news"],
        "fundamental": ["fundamental"],
        "technical": ["technical"],
        "valuation": ["valuation"],
        "news": ["news"],
    }
    agents = agent_map.get(analysis_type, agent_map["full"])
    return [Send(agent, state) for agent in agents]

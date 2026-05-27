"""
mcp_react.py — MCP 版 ReAct 循环

和 graph.py 中的 run_agent_react() 逻辑完全一致，但工具调用方式不同：
- 原版：从 agent 文件中 import 硬编码工具列表 → tool_obj.invoke()
- MCP版：从 MCP Server 动态发现工具 → client.call_tool()（通过协议转发）

这个模块是"桥梁"的体现——Agent 的思考和判断逻辑不变，
改变的只是"如何执行工具调用"。这就是 MCP 和 Function Call 的核心区别。
"""
import concurrent.futures
import threading

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


def run_agent_mcp(agent_type: str, state: dict, mode: str = "embedded",
                  mcp_tools=None, mcp_client=None) -> str:
    """
    MCP 版 Agent ReAct 循环。

    参数:
        agent_type: 'fundamental', 'technical', 'valuation', 'news', 'summary'
        state: AnalysisState 字典
        mode: 'embedded'（stdio）或 'sse'（HTTP）
        mcp_tools: 预加载的 MCP 工具列表（LangChain StructuredTool）
        mcp_client: MCPClient 实例（用于直接 call_tool / read_resource）

    对比 run_agent_react() 的改动只有两处：
    1. 工具来源：MCP Server（动态发现）vs 硬编码 import
    2. 工具执行：通过 MCP 协议（client.call_tool）vs 直接 Python 调用（tool_obj.invoke）
    """
    # 如果没有预加载的工具，现加载
    if mcp_tools is None:
        from src.mcp_integration.mcp_loader import load_mcp_tools, get_mcp_client
        mcp_tools = load_mcp_tools(mode)
        mcp_client = get_mcp_client(mode)

    # LLM 超时和 Agent 超时（复用 graph.py 的配置）
    LLM_TIMEOUT = 60
    AGENT_TIMEOUT = 180  # 与 graph.py 保持一致

    # 工具超时保护
    import socket
    socket.setdefaulttimeout(LLM_TIMEOUT)

    def _execute():
        # 获取原始 LLM（不是 chain），我们手动 bind MCP tools
        from src.graph import get_llm
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        llm = get_llm()
        stock_code = state.get("stock_code", "")

        # Agent system prompts（简化版，和原版 agent 模板一致）
        system_prompts = {
            "fundamental": "你是基本面分析Agent，负责分析股票的财务健康状况。请调用可用工具获取财务数据，分析ROE、营收增速、资产负债率等关键指标。",
            "technical": "你是技术面分析Agent，负责分析股票的量价关系和趋势。请调用可用工具获取行情数据，分析趋势、支撑压力位、波动率等。",
            "valuation": "你是估值分析Agent，负责评估股票的估值水平。请调用可用工具获取估值数据，分析PE/PB/PS、PEG等指标。",
            "news": "你是新闻舆情分析Agent，负责分析股票相关的新闻和舆情。请调用可用工具获取新闻数据，分析市场情绪和重大事件。",
            "summary": "你是综合分析Agent，负责汇总各维度分析结果。请调用可用工具进行交叉验证和评分，输出综合投资报告。",
        }

        system_text = system_prompts.get(agent_type, f"你是{agent_type}分析Agent。")

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_text),
            MessagesPlaceholder("messages"),
        ])
        llm_with_tools = llm.bind_tools(mcp_tools)
        chain = prompt | llm_with_tools

        # 构建初始消息
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

        max_steps = 12
        step = 0

        while step < max_steps:
            step += 1
            try:
                response = chain.invoke({"messages": messages})

            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    raise RuntimeError(f"[{agent_type}] LLM 请求超时（{LLM_TIMEOUT}秒），请检查 API 连接或网络状态")
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

                # 关键差异：工具调用通过 MCP 协议转发
                # 原版: result = tool_obj.invoke(tool_args)  ← 直接 Python 调用
                # MCP版: result = mcp_client.call_tool(tool_name, tool_args)  ← 协议转发
                tool_obj = next((t for t in mcp_tools if t.name == tool_name), None)
                if tool_obj:
                    try:
                        # 两种方式都可以：通过 LangChain 包装或直接通过 MCP 协议
                        result = tool_obj.invoke(tool_args)
                        messages.append(ToolMessage(content=str(result)[:4000], tool_call_id=tool_call_id))
                    except Exception as e:
                        messages.append(ToolMessage(content=f"[MCP] 工具调用失败: {str(e)}", tool_call_id=tool_call_id))
                else:
                    messages.append(ToolMessage(content=f"[MCP] 未找到工具: {tool_name}（可用工具: {[t.name for t in mcp_tools]}）", tool_call_id=tool_call_id))

        last_msg = messages[-1] if messages else AIMessage(content="[MCP] 分析超时")
        return last_msg.content if hasattr(last_msg, 'content') else str(last_msg)

    # 线程池 + 超时兜底（和原版一致）
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_execute)
        try:
            return future.result(timeout=AGENT_TIMEOUT)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(
                f"[{agent_type}] MCP Agent 执行超时（{AGENT_TIMEOUT}秒），"
                f"请检查 MCP Server 是否正常运行、API Key 是否正确"
            )

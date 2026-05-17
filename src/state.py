"""
state.py — LangGraph 全局状态定义
定义分析流程中各节点共享的数据结构，用于传递用户输入、工具结果、Agent 输出等。
"""
from typing import TypedDict, Annotated, List, Optional
from operator import add
from langgraph.graph.message import add_messages


class AgentResult(TypedDict):
    """单个分析 Agent 的结果"""
    agent_name: str          # "fundamental" / "technical" / "valuation" / "news"
    analysis: str            # 分析文本结果
    confidence: float        # 置信度 0~1
    data_sources: List[str]  # 引用的数据来源


class EvaluationResult(TypedDict):
    """评判 Agent 的打分结果"""
    hallucination_score: float    # 幻觉检测得分 0~1
    reasoning_score: float        # 推理质量得分 0~1
    risk_sensitivity: float       # 风险敏感度得分 0~1
    tool_accuracy: float          # 工具调用准确率 0~1
    overall_score: float          # 综合得分


class AnalysisState(TypedDict):
    """LangGraph 编排的全局状态"""
    # 用户输入
    stock_code: str               # 股票代码，如 "600519.SH"
    analysis_type: str            # "full"(全量分析) / "fundamental" / "technical" / "valuation" / "news"
    eval_mode: bool               # 是否开启评判模式
    eval_models: List[str]        # 参与对比的模型列表 ["gpt-4o", "deepseek-chat"]

    # 原始数据（由 MCP Server 获取）
    raw_data: dict                # Tushare 原始数据缓存

    # Agent 结果
    agent_results: Annotated[List[AgentResult], add]

    # 评判结果
    evaluation_results: List[EvaluationResult]  # 多模型对比结果

    # 中间消息（LangGraph add_messages 注解）
    messages: Annotated[List, add_messages]

    # 最终输出
    summary: str                  # Summary Agent 生成的汇总摘要
    final_verdict: str            # 投资结论：看好/中性/看空

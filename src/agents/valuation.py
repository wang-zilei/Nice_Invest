"""
valuation.py — 估值分析 Agent
基于 ReAct 模式，调用 Tushare 估值指标 + 计算工具，生成估值分析报告。
使用统一输出模板（template.py），确保面试可解释性。
"""
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.mcp_tools.tushare_api import get_stock_basic, get_financial_report
from src.mcp_tools.calculator import calc_pe_growth, calc_financial_ratio
from src.mcp_tools.news_api import get_stock_valuation_snapshot
from src.mcp_tools.yahoo_api import get_stock_info_yahoo
from src.agents.template import build_system_prompt, VALUATION_JSON_SCHEMA


@tool
def get_valuation_metrics(ts_code: str) -> str:
    """获取股票估值指标（Tushare Pro），包括 PE/PB/PS、总市值、流通市值等"""
    return get_stock_basic(ts_code)


@tool
def get_valuation_backup(ts_code: str) -> str:
    """获取估值指标备选（akshare），当 Tushare 限流时使用。包含 PE/PB/PS/市值/股息率等"""
    return get_stock_valuation_snapshot(ts_code)


# ---- yfinance 兜底数据源（海外备选，国内服务正常时不需要） ----
@tool
def get_valuation_data_yahoo(ts_code: str) -> str:
    """【兜底】获取股票估值数据（Yahoo Finance），当国内数据源均不可用时使用。包括 PE(TTM)/远期PE/PB/PS/PEG/股息率/市值/Beta 等"""
    return get_stock_info_yahoo(ts_code)


@tool
def get_financials_for_valuation(ts_code: str, period: str = "") -> str:
    """获取财务报表核心指标，包括 ROE、净利润、营收增速、资产负债率等"""
    return get_financial_report(ts_code, period)


@tool
def calculate_peg(pe: float, profit_growth_rate: float) -> str:
    """计算 PEG 指标，评估市盈率与盈利增长的匹配度"""
    result = calc_pe_growth(pe, profit_growth_rate)
    if result.get("peg") is not None:
        return f"PEG={result['peg']} | PE={result['pe']} | 净利润增速={result['profit_growth_rate']}% | 判断: {result['interpretation']}"
    return result.get("interpretation", "计算失败")


@tool
def calculate_liquidity_ratio(current_assets: float, current_liabilities: float) -> str:
    """计算流动比率和速动比率，评估短期偿债能力对估值的影响"""
    result = calc_financial_ratio(current_assets, current_liabilities)
    if "error" in result:
        return result["error"]
    parts = [f"流动比率={result.get('current_ratio', 'N/A')}({result.get('current_ratio_note', '')})"]
    if "quick_ratio" in result:
        parts.append(f"速动比率={result['quick_ratio']}({result.get('quick_ratio_note', '')})")
    return " | ".join(parts)


# 工具优先级: akshare → tushare → yahoo
VALUATION_TOOLS = [get_valuation_backup, get_valuation_metrics, get_valuation_data_yahoo, get_financials_for_valuation, calculate_peg, calculate_liquidity_ratio]

VALUATION_SYSTEM_PROMPT = build_system_prompt(
    agent_role="你是一位资深估值分析师，擅长通过多维度估值指标判断股票是否被合理定价。",

    analysis_dimensions="""你的分析维度包括：
1. 相对估值：PE/PB/PS 当前值及历史分位判断，行业横向对比
2. 成长估值：PEG 评估市盈率与盈利增速的匹配度
3. 绝对估值参考：股息率、净资产收益率对估值的支撑
4. 财务健康对估值的影响：资产负债结构、流动性对折溢价的解释""",

    agent_instructions="""工作流程（akshare 国内源优先，Yahoo 兜底）：
1. **首选**调用 get_valuation_backup 获取 akshare 估值快照（国内源，免费不限流，含 PE/PB/PS/市值/股息率等）
2. 如 akshare 数据不足，再调用 get_valuation_metrics 获取 Tushare PE/PB/PS/市值等数据补充
3. 如仍不足（海外服务器场景），调用 get_valuation_data_yahoo 获取 Yahoo Finance 估值数据兜底
4. 调用 get_financials_for_valuation 获取 ROE、净利润增速等财务数据（Tushare 补充）
5. 基于获取的数据，调用 calculate_peg 判断成长估值匹配度
6. 如需补充流动性分析，调用 calculate_liquidity_ratio
7. 按五段式模板输出估值分析报告

注意：
- 必须区分"便宜"和"低估"——低 PE 可能反映市场对行业前景的谨慎预期
- 历史分位对比优先使用真实数据，无法获取时标注 [来源: LLM 知识库，非实时数据]
- 银行股 PB < 1 需结合 ROE 和不良率解释
- **数据源优先级**: akshare（国内主力）→ Tushare（补充）→ Yahoo Finance（海外兜底）
- **限流处理**：如果 Tushare 返回"调用频次超限"或"限流"错误，不要重试""",
)

VALUATION_SYSTEM_PROMPT += VALUATION_JSON_SCHEMA

VALUATION_SYSTEM_PROMPT += """

## Role
You are a financial analyst who MUST communicate entirely in Chinese. All responses, analysis, and tool calls must be in Chinese.
"""

def create_valuation_agent(llm: ChatOpenAI) -> object:
    """创建估值分析 Agent（ReAct 模式）"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", VALUATION_SYSTEM_PROMPT),
        MessagesPlaceholder("messages"),
    ])
    llm_with_tools = llm.bind_tools(VALUATION_TOOLS)
    return prompt | llm_with_tools

"""
technical.py — 技术面分析 Agent
基于 ReAct 模式，调用 Tushare 日线数据，生成量价技术分析报告。
使用统一输出模板（template.py），确保面试可解释性。
"""
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.mcp_tools.tushare_api import get_daily_quote
from src.mcp_tools.news_api import get_daily_quote_ak
from src.mcp_tools.yahoo_api import get_daily_quote_yahoo
from src.agents.template import build_system_prompt, TECHNICAL_JSON_SCHEMA


@tool
def get_technical_data(ts_code: str, start_date: str = "", end_date: str = "") -> str:
    """获取股票技术面数据（Tushare Pro），包括 OHLCV（开高低收量）和涨跌幅"""
    return get_daily_quote(ts_code, start_date, end_date)


@tool
def get_technical_data_backup(ts_code: str) -> str:
    """获取技术面数据备选（akshare，免费不限流），包括最近60个交易日OHLCV及MA均线。当 Tushare 限流时优先使用"""
    return get_daily_quote_ak(ts_code, days=60)


# ---- yfinance 主力数据源（US-friendly，优先使用） ----
@tool
def get_technical_data_yahoo(ts_code: str) -> str:
    """【优先使用】获取股票技术面数据（Yahoo Finance），包括最近60个交易日OHLCV、MA均线、波动率等。从美国服务器可正常访问"""
    return get_daily_quote_yahoo(ts_code, days=60)


# 工具优先级: yahoo → akshare → tushare
TECHNICAL_TOOLS = [get_technical_data_yahoo, get_technical_data_backup, get_technical_data]

TECHNICAL_SYSTEM_PROMPT = build_system_prompt(
    agent_role="你是一位资深技术分析师，擅长通过量价数据判断股票的技术走势。",

    analysis_dimensions="""你的分析维度包括：
1. 趋势分析：中长期/短期价格趋势方向（上升/下降/横盘），高低点序列变化
2. 量价关系：成交量与价格变动是否配合，是否存在量价背离
3. 波动特征：价格波动率变化趋势，振幅收窄/扩大信号
4. 关键价位：通过近期高低点识别支撑位和压力位""",

    agent_instructions="""工作流程（Yahoo Finance 优先，国内源兜底）：
1. **首选**调用 get_technical_data_yahoo 获取 Yahoo Finance 日线行情（美国服务器可正常访问，免费不限流，含60日 OHLCV + MA + 波动率）
2. 如需要更长的历史数据或 Yahoo 数据不足，再调用 get_technical_data_backup 获取 akshare 日线数据补充
3. 如仍不足，调用 get_technical_data 获取 Tushare 日线数据进一步补充
4. 基于真实数据计算关键指标：区间涨跌幅、波动率、均线位置
5. 识别支撑位（近期低点密集区）和压力位（近期高点密集区）
6. 按五段式模板输出技术分析报告

注意：
- 必须基于实际 OHLCV 数据计算，不得凭空编造价位
- 趋势判断需引用具体时间段和价格变化幅度
- 技术分析不构成买卖建议，需在风险提示中声明
- **数据源优先级**: Yahoo Finance → akshare（国内备选）→ Tushare（最后兜底）""",
)

TECHNICAL_SYSTEM_PROMPT += TECHNICAL_JSON_SCHEMA

TECHNICAL_SYSTEM_PROMPT += """

## Role
You are a financial analyst who MUST communicate entirely in Chinese. All responses, analysis, and tool calls must be in Chinese.
"""

def create_technical_agent(llm: ChatOpenAI) -> object:
    """创建技术面分析 Agent（ReAct 模式）"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", TECHNICAL_SYSTEM_PROMPT),
        MessagesPlaceholder("messages"),
    ])
    llm_with_tools = llm.bind_tools(TECHNICAL_TOOLS)
    return prompt | llm_with_tools

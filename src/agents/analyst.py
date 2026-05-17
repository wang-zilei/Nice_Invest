"""
analyst.py — 基本面分析 Agent
基于 ReAct 模式，调用 Tushare 财务数据 + 计算工具，生成财务健康分析报告。
使用统一输出模板（template.py），确保面试可解释性。
"""
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.mcp_tools.tushare_api import get_stock_basic, get_financial_report
from src.mcp_tools.calculator import calc_dupont, calc_financial_ratio, calc_cagr
from src.mcp_tools.news_api import get_stock_financial_summary
from src.agents.template import build_system_prompt, FUNDAMENTAL_JSON_SCHEMA


# 定义基本面分析工具
@tool
def get_fundamental_data(ts_code: str) -> str:
    """获取股票基本面数据（Tushare Pro），包括基本信息、财务指标、利润表等"""
    basic = get_stock_basic(ts_code)
    financial = get_financial_report(ts_code)
    return basic + "\n\n" + financial


@tool
def get_fundamental_backup(ts_code: str) -> str:
    """获取基本面数据备选（akshare），当 Tushare 限流时使用。包含 ROE、营收、利润率、资产负债率等核心财务指标"""
    return get_stock_financial_summary(ts_code)


@tool
def calculate_dupont_analysis(net_profit_margin: float, asset_turnover: float, equity_multiplier: float) -> str:
    """执行杜邦分析，计算 ROE 并拆解为净利率、资产周转率、权益乘数三因素"""
    result = calc_dupont(net_profit_margin, asset_turnover, equity_multiplier)
    return f"杜邦分析结果: ROE={result['roe']}% | 净利率={result['net_profit_margin']}% | 资产周转率={result['asset_turnover']} | 权益乘数={result['equity_multiplier']} | 解读: {result['interpretation']}"


@tool
def calculate_growth_rate(start_value: float, end_value: float, years: int) -> str:
    """计算复合年增长率 (CAGR)，用于分析营收/利润增长趋势"""
    result = calc_cagr(start_value, end_value, years)
    if "error" in result:
        return result["error"]
    return f"CAGR: {result['cagr']}% | 起始值={result['start_value']} | 终值={result['end_value']} | 年数={result['years']}年 | 解读: {result['interpretation']}"


FUNDAMENTAL_TOOLS = [get_fundamental_data, get_fundamental_backup, calculate_dupont_analysis, calculate_growth_rate]

# 基本面分析 Agent 的系统提示词（使用统一模板）
FUNDAMENTAL_SYSTEM_PROMPT = build_system_prompt(
    agent_role="你是一位资深的基本面分析专家，擅长通过财务数据评估企业的经营健康状况。",

    analysis_dimensions="""你的分析维度包括：
1. 盈利能力：ROE、净利润率、毛利率趋势，杜邦三因素拆解
2. 成长性：营收增速、净利润增速、近3年CAGR
3. 偿债能力：资产负债率、流动比率、速动比率
4. 运营效率：资产周转率、权益乘数变化趋势""",

    agent_instructions="""工作流程（akshare 优先，避免 Tushare 限流）：
1. **首选**调用 get_fundamental_backup 获取 akshare 财务摘要（免费、不限流、包含 ROE/营收/利润率/资产负债率等核心指标）
2. 再调用 get_fundamental_data 获取 Tushare Pro 数据作为补充（含更全的财务指标表）
3. 如 Tushare 限流或返回空数据，不影响分析——akshare 数据已足够覆盖核心指标
4. 根据获取的数据，必要时调用 calculate_dupont_analysis 进行杜邦拆解
5. 如数据中包含多年营收/利润数据，调用 calculate_growth_rate 计算 CAGR
6. 综合所有数据，按五段式模板输出分析报告

注意：
- 银行股分析需额外关注不良率、拨备覆盖率、净息差、资本充足率等指标
- 如所有数据接口均返回空，必须在元信息中如实声明，使用 LLM 知识库兜底并标注
- 杜邦分析和CAGR计算需要从财务数据中提取参数后再调用
- **限流处理**：如果 Tushare 返回"调用频次超限"或"限流"错误，不要重试，直接使用 akshare 数据继续分析""",
)

FUNDAMENTAL_SYSTEM_PROMPT += FUNDAMENTAL_JSON_SCHEMA

FUNDAMENTAL_SYSTEM_PROMPT += """

## Role
You are a financial analyst who MUST communicate entirely in Chinese. All responses, analysis, and tool calls must be in Chinese.
"""

def create_fundamental_agent(llm: ChatOpenAI) -> object:
    """创建基本面分析 Agent（ReAct 模式）"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", FUNDAMENTAL_SYSTEM_PROMPT),
        MessagesPlaceholder("messages"),
    ])
    llm_with_tools = llm.bind_tools(FUNDAMENTAL_TOOLS)
    return prompt | llm_with_tools

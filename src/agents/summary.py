"""
summary.py — 综合汇总 Agent（ReAct 模式）
带工具的汇总 Agent，具备交叉验证、指标核实、加权评分能力。
输出完整的五段式综合投资报告。
"""
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from src.agents.template import SUMMARY_JSON_SCHEMA


@tool
def cross_validate_agents(agent_a_name: str, agent_a_claim: str, agent_b_name: str, agent_b_claim: str) -> str:
    """
    交叉验证两个 Agent 的分析结论是否存在矛盾。
    参数:
        agent_a_name: Agent A 名称（如"基本面"）
        agent_a_claim: Agent A 的关键结论
        agent_b_name: Agent B 名称（如"估值"）
        agent_b_claim: Agent B 的关键结论
    返回: 矛盾分析结果
    """
    return f"""【交叉验证】{agent_a_name} vs {agent_b_name}
{agent_a_name}结论: {agent_a_claim}
{agent_b_name}结论: {agent_b_claim}
→ 请判断上述两条结论是否存在矛盾。如存在矛盾，分析可能原因（数据时间差/口径差异/行业特性/分析维度不同）。
如不存在矛盾，说明两条结论如何互相印证。"""


@tool
def verify_data_consistency(metric_name: str, value_a: str, source_a: str, value_b: str, source_b: str) -> str:
    """
    核实同一指标在两个数据源中的一致性。
    参数:
        metric_name: 指标名称（如"ROE"）
        value_a: 数据源 A 的值
        source_a: 数据源 A 的名称
        value_b: 数据源 B 的值
        source_b: 数据源 B 的名称
    返回: 一致性分析
    """
    return f"""【数据一致性核实】{metric_name}
{source_a}: {value_a}
{source_b}: {value_b}
→ 请判断两组数据是否一致。如偏差超过 10%，分析差异原因（报告期不同/口径不同/数据质量问题）。
输出格式：一致性结论 [一致 / 轻微偏差(<10%) / 显著偏差(>10%)]，+ 原因说明"""


@tool
def calculate_weighted_score(fundamental_score: float, technical_score: float,
                             valuation_score: float, news_score: float) -> str:
    """
    基于四个维度得分计算加权综合评分。
    权重分配：基本面 35% / 技术面 20% / 估值 30% / 新闻舆情 15%
    参数: 各维度 0-10 分
    返回: 加权总分及解读
    """
    weights = {"基本面": 0.35, "技术面": 0.20, "估值": 0.30, "新闻舆情": 0.15}
    weighted = (
        fundamental_score * weights["基本面"] +
        technical_score * weights["技术面"] +
        valuation_score * weights["估值"] +
        news_score * weights["新闻舆情"]
    )
    if weighted >= 8.0:
        level = "强烈推荐"
    elif weighted >= 6.5:
        level = "推荐关注"
    elif weighted >= 5.0:
        level = "中性观望"
    elif weighted >= 3.5:
        level = "谨慎回避"
    else:
        level = "建议回避"

    return f"""【加权综合评分】
- 基本面({fundamental_score}/10 × 35%) = {fundamental_score * 0.35:.1f}
- 技术面({technical_score}/10 × 20%) = {technical_score * 0.20:.1f}
- 估值({valuation_score}/10 × 30%) = {valuation_score * 0.30:.1f}
- 新闻舆情({news_score}/10 × 15%) = {news_score * 0.15:.1f}
- 加权总分: {weighted:.1f} / 10
- 投资建议等级: {level}"""


SUMMARY_TOOLS = [cross_validate_agents, verify_data_consistency, calculate_weighted_score]

SUMMARY_SYSTEM_PROMPT = """你是一位资深投资顾问，负责汇总四个维度（基本面、技术面、估值、新闻舆情）的分析结果，产出综合投资报告。

## 输出铁律
1. **禁止暴露思考过程**：最终输出必须是完整的综合投资报告，严禁出现任何思考过程、内心独白、过渡性语言。禁止出现"看起来..."、"好的"、"现在我来..."、"下面给出..."、"让我先..."等字样。直接输出报告正文。
1b. **禁止 Markdown 格式符号**：严禁使用 Markdown 格式符号（`#`、`##`、`###`、`*`、`- `、`---`、`**`、`__` 等，表格 `|` 管道符除外）。报告使用纯文本，标题使用"一、二、三"编号区分层级，段落之间用空行分隔。表格使用 `|` 管道符格式（会由前端渲染为对齐表格，不会显示 `|` 符号）。
2. **交叉验证优先**：必须先调用 cross_validate_agents 检查不同 Agent 之间的结论是否存在矛盾
3. **数据一致性**：对关键指标（ROE、PE、营收增速等）调用 verify_data_consistency 核实不同来源的一致性
4. **加权评分**：调用 calculate_weighted_score 计算综合评分，不得手动估算
5. **标注不确定性**：对数据缺失或结论矛盾的维度，明确标注置信度下降

## 输出格式要求

**禁止输出任何标题行**（严禁出现 `#`、`##`、`---` 等 Markdown 标记符号）。报告直接从"一、投资倾向"开始。

请严格按以下五段式输出综合投资报告：

一、投资倾向
倾向：[强烈看好 / 看好 / 中性 / 看空 / 强烈看空]
置信度：[高 / 中 / 低]，说明影响置信度的因素

二、交叉分析
列出各 Agent 核心结论之间的印证与矛盾点
对矛盾点给出解释或判断

三、综合评分
各维度得分及加权计算过程（使用 calculate_weighted_score 工具）
与同行业对比（如有数据）

四、情景分析
乐观情景：触发条件 + 预期表现
基准情景：最可能的发展路径
悲观情景：触发条件 + 下行风险

五、风险清单
按影响程度从高到低排列，每条风险包含：
风险描述
影响程度：[高/中/低]
发生概率：[高/中/低]
应对建议

""" + SUMMARY_JSON_SCHEMA + """

## Role
You are a financial advisor who MUST communicate entirely in Chinese. All responses, analysis, and tool calls must be in Chinese.
"""


def create_summary_agent(llm: ChatOpenAI) -> object:
    """创建综合汇总 Agent（ReAct 模式，带交叉验证工具）"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUMMARY_SYSTEM_PROMPT),
        MessagesPlaceholder("messages"),
    ])
    llm_with_tools = llm.bind_tools(SUMMARY_TOOLS)
    return prompt | llm_with_tools

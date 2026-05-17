"""
news.py — 新闻舆情分析 Agent
基于 ReAct 模式，调用 akshare 新闻数据（东方财富+财联社+全球财经），生成舆情与事件分析报告。
使用统一输出模板（template.py），确保面试可解释性。
"""
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.mcp_tools.news_api import get_combined_news, get_eastmoney_news, get_cls_global_news
from src.mcp_tools.tushare_api import search_stock
from src.agents.template import build_system_prompt, NEWS_JSON_SCHEMA


@tool
def get_stock_news_combined(ts_code: str) -> str:
    """获取指定股票的综合新闻（含东方财富个股新闻 + 财联社电报 + 全球财经新闻）"""
    return get_combined_news(ts_code)


@tool
def get_stock_news_em(ts_code: str) -> str:
    """获取东方财富个股新闻，聚焦单只股票的资讯"""
    return get_eastmoney_news(ts_code)


@tool
def get_market_telegraph() -> str:
    """获取财联社全球财经快讯，了解宏观市场动态"""
    return get_cls_global_news()


@tool
def search_stock_by_keyword(keyword: str) -> str:
    """按关键词搜索股票，用于将中文名称转换为 ts_code"""
    return search_stock(keyword)


NEWS_TOOLS = [get_stock_news_combined, get_stock_news_em, get_market_telegraph, search_stock_by_keyword]

NEWS_SYSTEM_PROMPT = build_system_prompt(
    agent_role="你是一位资深金融舆情分析师，擅长通过新闻资讯判断市场情绪和重大事件对股价的潜在影响。",

    analysis_dimensions="""你的分析维度包括：
1. 舆情情感：近期新闻整体倾向性（正面/负面/中性），情感分布统计
2. 重大事件：提取可能影响股价的重大事件（业绩公告、并购重组、监管处罚、高管变动等）
3. 行业政策：影响该股票所在行业的政策或监管变化
4. 市场关注度：新闻频率和热度变化反映的市场关注程度""",

    agent_instructions="""工作流程：
1. 首选调用 get_stock_news_combined 获取综合新闻（个股+市场+全球）
2. 如需深入个股新闻，调用 get_stock_news_em 补充
3. 如需了解宏观市场情绪，调用 get_market_telegraph 获取财联社电报
4. 按五段式模板输出舆情分析报告

注意：
- 严格区分"事件事实"和"市场解读"，事实引用原文，解读标注为分析观点
- 如 akshare 数据获取失败，元信息中如实声明，使用 Tushare search_stock 或 LLM 知识库兜底
- 不得虚构新闻事件，不得引用无法验证的消息来源
- 数据来源标记：[来源: 东方财富] / [来源: 财联社] / [来源: LLM 知识库]""",
)

NEWS_SYSTEM_PROMPT += NEWS_JSON_SCHEMA

NEWS_SYSTEM_PROMPT += """

## Role
You are a financial analyst who MUST communicate entirely in Chinese. All responses, analysis, and tool calls must be in Chinese.
"""

def create_news_agent(llm: ChatOpenAI) -> object:
    """创建新闻舆情分析 Agent（ReAct 模式）"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", NEWS_SYSTEM_PROMPT),
        MessagesPlaceholder("messages"),
    ])
    llm_with_tools = llm.bind_tools(NEWS_TOOLS)
    return prompt | llm_with_tools

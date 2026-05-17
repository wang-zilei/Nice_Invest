"""
template.py — Agent 输出模板与铁律
所有分析 Agent 共享的输出结构约束，确保面试可解释性。

两段式输出：Markdown正文（人类阅读） + JSON代码块（前端渲染）
"""

# ============================================================
# 四条铁律（所有 Agent 必须遵守）
# ============================================================
IRON_RULES = """## 输出铁律（必须严格遵守，违反将导致输出被拒绝）

1. **禁止暴露思考过程（最重要规则）**：
   - 你是一个投资分析报告生成器，不是聊天助手
   - 严禁输出任何思考过程、推理链、内心独白、过渡性语言
   - 严禁出现以下任何字样："看起来"、"好的"、"数据已获取"、"现在我来"、"下面给出"、"我手动计算"、"让我整合"、"首先我需要"、"接下来"、"最后"、"基于以上"、"我们已经"、"根据获取"、"让我先"、"综合来看"
   - 严禁使用 思考/思考 标签或类似标记包裹内容
   - 你的输出从第一个章节标题（"一、"）直接开始，前面不得有任何文字
   - 想象你是打印机：只输出最终报告，不输出你在想什么

1b. **禁止 Markdown 格式符号（最重要规则之一）**：严禁使用以下 Markdown 格式符号：`#`、`##`、`---`、`**粗体**`、`*斜体*`、`- 列表`、`* 列表` 等。唯一例外：表格可以使用 `|` 管道符格式（会由前端渲染为对齐表格，不会显示 `|` 符号）。标题使用"一、二、三"或"1.1、1.2"中文编号区分层级。数据来源用 `[来源: XXX]` 标注。段落之间用空行分隔。

2. **数据来源标注**：每个关键数据点必须标注来源，格式为 `[来源: Tushare Pro]` / `[来源: akshare]` / `[来源: LLM 知识库]` / `[来源: 计算得出]`

3. **失败兜底声明**：当数据接口调用失败或返回空数据时，必须明确声明"数据获取失败"，不得凭空捏造数值。可使用 LLM 知识库补充但须标注 `[来源: LLM 知识库，非实时数据]`

4. **量化优于定性**：能用具体数字就不用模糊形容词。不说"盈利能力较好"，要说"ROE 12.5%，高于行业均值 10.2%"

5. **不确定性标注**：对基于估算、推测、或 LLM 知识的结论，明确标注 `[注: 该结论基于估算/LLM知识，存在不确定性]`

6. **完整输出**：你的分析报告必须完整详尽，每个分析维度至少写200字，不得偷懒缩减内容。报告面向专业投资者，信息密度要高。"""

# ============================================================
# 两段式输出要求（所有 Agent 共享）
# ============================================================
TWO_PART_OUTPUT = """## 输出格式要求

你的输出包含两部分：

1. **纯文本分析报告正文**（人类阅读）
   - 按五段式结构撰写完整的分析报告
   - 语言专业、数据详实、结构清晰
   - 禁止使用任何思考过程或过渡性语言
   - 禁止使用 Markdown 格式符号（`#`、`**`、`*`、`---` 等，表格 `|` 除外）
   - 使用"一、二、三"等中文编号区分标题层级
   - 数据来源用 [来源: XXX] 标注

2. **JSON 数据块**（机器读取，放在输出末尾）
   - 在纯文本正文之后，用 ```json 代码块包裹
   - 严格按指定字段结构输出
   - 所有数值字段必须是数字类型（非字符串）
   - JSON 块不属于报告正文，前端不会展示它

格式示例：
```
一、元信息
分析对象：XXXX（XXXXXX）
...

二、核心结论
...

（五段式正文完整纯文本内容）

```json
{{"report_key": {{...}}}}
```"""

# ============================================================
# 统一输出模板（每个 Agent 独立使用）
# ============================================================
OUTPUT_TEMPLATE = """## Markdown 正文输出要求

请严格按照以下五段式结构输出分析报告。注意：这是最终报告，面向投资者阅读，必须专业、直接、无冗余。严禁使用 Markdown 格式符号（`#`、`**`、`---` 等，表格 `|` 管道符除外）。

一、元信息
分析对象：{{stock_name}}（{{stock_code}}）
分析时间：当前日期
数据来源：[列出实际调用的工具及返回状态]
数据完整性：[完整 / 部分缺失 / 严重缺失]，缺失项说明

二、核心结论
一句话总结：（不超过 50 字）
综合评分：X.X / 10
投资倾向：[看好 / 中性 / 看空]，一句话说明理由

三、详细分析
按分析维度逐一展开，每个维度一个小节（3.1、3.2...）：
关键发现：量化表述，引用具体数据
数据支撑：标注来源
与行业/历史对比：如有数据则对比，无数据则标注缺失

四、关键指标明细表
使用表格格式（每行以 | 开头，用于前端渲染对齐表格）：
| 指标名称 | 数值 | 行业均值/基准 | 评价 | 数据来源 |
|---------|------|-------------|------|---------|
| ROE | 12.5% | 10.2% | 高于行业 | [来源: Tushare Pro] |
| ... | ... | ... | ... | ... |

五、风险提示
风险1：[具体风险描述]，影响程度：[高/中/低]
风险2：...
数据质量风险：[数据缺失/限流/兜底导致的结论不确定性]"""


def build_system_prompt(agent_role: str, analysis_dimensions: str, agent_instructions: str) -> str:
    """构建标准化的 Agent 系统提示词（LangChain f-string 模板格式，{{ 为转义花括号）"""
    return f"""{agent_role}

{IRON_RULES}

{analysis_dimensions}

{agent_instructions}

{TWO_PART_OUTPUT}

{OUTPUT_TEMPLATE}"""


# ============================================================
# 各 Agent JSON Schema 定义
# 注意：所有花括号已用 {{ 和 }} 转义，因为会经 ChatPromptTemplate.from_messages 的 f-string 模板引擎解析
# ============================================================

FUNDAMENTAL_JSON_SCHEMA = """
## JSON 输出字段（fundamental_report）
```json
{{
  "fundamental_report": {{
    "key_metrics": {{
      "roe": "数字(%)",
      "net_profit_margin": "数字(%)",
      "gross_margin": "数字(%)",
      "revenue_growth": "数字(%)",
      "net_profit_growth": "数字(%)",
      "debt_ratio": "数字(%)",
      "current_ratio": "数字",
      "asset_turnover": "数字"
    }},
    "dupont_decomposition": {{
      "net_profit_margin_pct": "数字",
      "asset_turnover": "数字",
      "equity_multiplier": "数字",
      "roe_pct": "数字"
    }},
    "cagr": {{ "revenue_cagr_3y": "数字或null", "net_profit_cagr_3y": "数字或null" }},
    "score": "数字(0-10)",
    "data_completeness": "complete | partial | severely_lacking"
  }}
}}
```"""

TECHNICAL_JSON_SCHEMA = """
## JSON 输出字段（technical_report）
```json
{{
  "technical_report": {{
    "key_metrics": {{
      "latest_price": "数字",
      "ma_5": "数字或null",
      "ma_20": "数字或null",
      "ma_60": "数字或null",
      "volatility_20d": "数字(%)",
      "volume_ratio": "数字"
    }},
    "price_range": {{ "support": "数字", "resistance": "数字" }},
    "volume_trend": "放量上涨 | 缩量下跌 | 量价配合 | 量价背离 | 正常",
    "trend_signal": "上升趋势 | 下降趋势 | 横盘震荡 | 无法判断",
    "score": "数字(0-10)",
    "data_completeness": "complete | partial | severely_lacking"
  }}
}}
```"""

VALUATION_JSON_SCHEMA = """
## JSON 输出字段（valuation_report）
```json
{{
  "valuation_report": {{
    "key_metrics": {{
      "pe_ttm": "数字或null",
      "pb": "数字或null",
      "ps_ttm": "数字或null",
      "peg": "数字或null",
      "dividend_yield": "数字(%)或null"
    }},
    "peer_comparison": {{
      "industry_avg_pe": "数字或null",
      "industry_avg_pb": "数字或null",
      "valuation_level": "低估 | 合理 | 高估 | 无法判断"
    }},
    "score": "数字(0-10)",
    "data_completeness": "complete | partial | severely_lacking"
  }}
}}
```"""

NEWS_JSON_SCHEMA = """
## JSON 输出字段（news_report）
```json
{{
  "news_report": {{
    "key_metrics": {{
      "total_news_count": "数字",
      "positive_count": "数字",
      "negative_count": "数字",
      "neutral_count": "数字"
    }},
    "sentiment": "正面 | 中性偏正面 | 中性 | 中性偏负面 | 负面",
    "major_events": [
      {{
        "event": "事件描述",
        "impact": "正面 | 负面 | 中性",
        "severity": "high | medium | low"
      }}
    ],
    "score": "数字(0-10)",
    "data_completeness": "complete | partial | severely_lacking"
  }}
}}
```"""

SUMMARY_JSON_SCHEMA = """
## JSON 输出字段（ReportData，供 Page 3 Report 渲染）
```json
{{
  "ReportData": {{
    "meta": {{ "stock_code": "代码", "stock_name": "名称", "analysis_time": "时间" }},
    "verdict": {{
      "direction": "看好 | 中性 | 看空",
      "confidence": "high | medium | low",
      "weighted_score": "数字(0-10)",
      "recommendation_level": "强烈推荐 | 推荐关注 | 中性观望 | 谨慎回避 | 建议回避"
    }},
    "scores": {{
      "fundamental": "数字",
      "technical": "数字",
      "valuation": "数字",
      "news": "数字",
      "weighted_total": "数字"
    }},
    "cross_analysis": [
      {{ "agent_pair": "A vs B", "consistent": "true或false", "detail": "说明" }}
    ],
    "scenarios": {{
      "bull": {{ "trigger": "触发条件", "expected_return": "预期表现" }},
      "base": {{ "description": "最可能路径" }},
      "bear": {{ "trigger": "触发条件", "downside_risk": "下行风险" }}
    }},
    "risks": [
      {{ "description": "风险描述", "impact": "high | medium | low", "probability": "high | medium | low", "mitigation": "应对建议" }}
    ]
  }}
}}
```"""

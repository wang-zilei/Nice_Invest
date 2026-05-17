"""
结构回归测试 — 验证所有模块导入、Graph 编译、Agent 工具链完整性
无需 API Key，纯结构验证。
用法: python tests/test_structural.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

passed = 0
failed = 0

def check(condition, label):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label}")

# ============================================================
# 1. 模板模块
# ============================================================
print("\n=== 1. 模板模块 ===")
from src.agents.template import build_system_prompt, IRON_RULES, OUTPUT_TEMPLATE
check(len(IRON_RULES) > 100, "IRON_RULES 非空")
check("数据来源标注" in IRON_RULES, "铁律1: 数据来源标注")
check("失败兜底声明" in IRON_RULES, "铁律2: 失败兜底声明")
check("量化优于定性" in IRON_RULES, "铁律3: 量化优于定性")
check("不确定性标注" in IRON_RULES, "铁律4: 不确定性标注")
check("元信息" in OUTPUT_TEMPLATE, "模板: 元信息段")
check("核心结论" in OUTPUT_TEMPLATE, "模板: 核心结论段")
check("详细分析" in OUTPUT_TEMPLATE, "模板: 详细分析段")
check("关键指标明细表" in OUTPUT_TEMPLATE, "模板: 关键指标表段")
check("风险提示" in OUTPUT_TEMPLATE, "模板: 风险提示段")

prompt = build_system_prompt("测试角色", "测试维度", "测试指令")
check("测试角色" in prompt, "build_system_prompt: 角色注入")
check("测试维度" in prompt, "build_system_prompt: 维度注入")
check("测试指令" in prompt, "build_system_prompt: 指令注入")
check(IRON_RULES.strip() in prompt, "build_system_prompt: 铁律注入")
check(OUTPUT_TEMPLATE.strip() in prompt, "build_system_prompt: 模板注入")

# ============================================================
# 2. MCP 工具模块
# ============================================================
print("\n=== 2. MCP 工具模块 ===")
from src.mcp_tools.calculator import calc_dupont, calc_pe_growth, calc_financial_ratio, calc_cagr

r = calc_dupont(0.15, 0.8, 2.5)
check(r["roe"] == 30.0, f"杜邦分析: ROE=30% (got {r['roe']}%)")
check("interpretation" in r, "杜邦分析: 含解读")

r = calc_pe_growth(20, 25)
check(r["peg"] == 0.8, f"PEG: 20/25=0.8 (got {r['peg']})")
check("低估" in r["interpretation"], "PEG: 低估判断")

r = calc_pe_growth(20, -5)
check(r["peg"] is None, "PEG: 负增长返回 None")

r = calc_cagr(100, 200, 5)
check(r["cagr"] > 0, f"CAGR: 正增长 (got {r['cagr']}%)")

r = calc_financial_ratio(200, 100)
check(r["current_ratio"] == 2.0, f"流动比率: 200/100=2.0 (got {r['current_ratio']})")

# akshare 懒加载
from src.mcp_tools.news_api import get_combined_news, get_stock_financial_summary, get_stock_valuation_snapshot
result = get_combined_news("000001.SZ")
check(isinstance(result, str) and len(result) > 0, "akshare 综合新闻: 返回错误提示（未安装akshare为预期行为）")

# ============================================================
# 3. Agent 模块
# ============================================================
print("\n=== 3. Agent 模块 ===")
from src.agents.analyst import FUNDAMENTAL_TOOLS, FUNDAMENTAL_SYSTEM_PROMPT
check(len(FUNDAMENTAL_TOOLS) == 4, f"基本面 Agent: 4 tools (got {len(FUNDAMENTAL_TOOLS)})")
check("get_fundamental_backup" in [t.name for t in FUNDAMENTAL_TOOLS], "基本面 Agent: 含 akshare 备选工具")
check("输出铁律" in FUNDAMENTAL_SYSTEM_PROMPT, "基本面 Agent: prompt 含铁律")
check("元信息" in FUNDAMENTAL_SYSTEM_PROMPT, "基本面 Agent: prompt 含模板")

from src.agents.technical import TECHNICAL_TOOLS, TECHNICAL_SYSTEM_PROMPT
check(len(TECHNICAL_TOOLS) == 1, f"技术面 Agent: 1 tool (got {len(TECHNICAL_TOOLS)})")
check("输出铁律" in TECHNICAL_SYSTEM_PROMPT, "技术面 Agent: prompt 含铁律")

from src.agents.valuation import VALUATION_TOOLS, VALUATION_SYSTEM_PROMPT
check(len(VALUATION_TOOLS) == 5, f"估值 Agent: 5 tools (got {len(VALUATION_TOOLS)})")
check("get_valuation_backup" in [t.name for t in VALUATION_TOOLS], "估值 Agent: 含 akshare 备选工具")
check("输出铁律" in VALUATION_SYSTEM_PROMPT, "估值 Agent: prompt 含铁律")

from src.agents.news import NEWS_TOOLS, NEWS_SYSTEM_PROMPT
check(len(NEWS_TOOLS) == 4, f"新闻 Agent: 4 tools (got {len(NEWS_TOOLS)})")
check("get_stock_news_combined" in [t.name for t in NEWS_TOOLS], "新闻 Agent: 含 akshare 综合新闻工具")
check("输出铁律" in NEWS_SYSTEM_PROMPT, "新闻 Agent: prompt 含铁律")

from src.agents.summary import SUMMARY_TOOLS, SUMMARY_SYSTEM_PROMPT
check(len(SUMMARY_TOOLS) == 3, f"Summary Agent: 3 tools (got {len(SUMMARY_TOOLS)})")
check("cross_validate_agents" in [t.name for t in SUMMARY_TOOLS], "Summary Agent: 含交叉验证工具")
check("verify_data_consistency" in [t.name for t in SUMMARY_TOOLS], "Summary Agent: 含数据一致性工具")
check("calculate_weighted_score" in [t.name for t in SUMMARY_TOOLS], "Summary Agent: 含加权评分工具")
check("交叉验证优先" in SUMMARY_SYSTEM_PROMPT, "Summary Agent: prompt 含交叉验证要求")
check("五段式" in SUMMARY_SYSTEM_PROMPT, "Summary Agent: prompt 含五段式要求")

# ============================================================
# 4. Graph 编译
# ============================================================
print("\n=== 4. Graph 编译 ===")
from src.graph import build_graph, get_llm, get_agent_llm, run_agent_react
check(callable(build_graph), "build_graph: 可调用")

# 验证所有 agent_type 都能创建
for at in ["fundamental", "technical", "valuation", "news", "summary"]:
    try:
        agent = get_agent_llm(at)
        check(agent is not None, f"get_agent_llm('{at}'): 创建成功")
    except Exception as e:
        check(False, f"get_agent_llm('{at}'): {e}")

# Graph 编译（不需要 API Key）
try:
    graph = build_graph()
    check(graph is not None, "Graph 编译: 成功")
except Exception as e:
    check(False, f"Graph 编译: {e}")

# ============================================================
# 5. State 定义
# ============================================================
print("\n=== 5. State 定义 ===")
from src.state import AnalysisState, AgentResult, EvaluationResult
# 验证 TypedDict 字段
expected_fields = ["stock_code", "analysis_type", "eval_mode", "eval_models",
                   "raw_data", "agent_results", "evaluation_results", "messages", "summary", "final_verdict"]
for f in expected_fields:
    check(f in AnalysisState.__annotations__, f"AnalysisState 字段: {f}")

# ============================================================
# 6. Summary Agent 工具逻辑
# ============================================================
print("\n=== 6. Summary Agent 工具逻辑 ===")
from src.agents.summary import cross_validate_agents, verify_data_consistency, calculate_weighted_score

r = cross_validate_agents.invoke({"agent_a_name": "基本面", "agent_a_claim": "ROE 12%，盈利能力良好", "agent_b_name": "估值", "agent_b_claim": "PE 5x，处于历史低位"})
check("交叉验证" in r, "cross_validate_agents: 返回结构化提示")

r = verify_data_consistency.invoke({"metric_name": "ROE", "value_a": "12.5%", "source_a": "Tushare", "value_b": "11.8%", "source_b": "akshare"})
check("数据一致性核实" in r, "verify_data_consistency: 返回结构化提示")

r = calculate_weighted_score.invoke({"fundamental_score": 7.0, "technical_score": 6.0, "valuation_score": 8.0, "news_score": 5.0})
check("加权综合评分" in r, "calculate_weighted_score: 返回结构化结果")
check(str(round(7.0 * 0.35, 1)) in r, "calculate_weighted_score: 含加权计算过程")

# ============================================================
# 汇总
# ============================================================
print(f"\n{'='*50}")
print(f"结果: {passed} PASS, {failed} FAIL")
if failed == 0:
    print("结构回归测试全部通过！")
else:
    print(f"存在 {failed} 个失败项，请检查。")
    sys.exit(1)

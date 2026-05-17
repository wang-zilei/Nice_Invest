"""
测试脚本 — 全量分析并输出完整结果到文件
用法: python tests/run_and_save.py
"""
import sys, os, io, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src.graph import build_graph
from src.state import AnalysisState

TEST_STOCK = "000001.SZ"
TEST_NAME = "平安银行"

print(f"Running full analysis for {TEST_STOCK} {TEST_NAME}...")

graph = build_graph()

result = graph.invoke({
    "stock_code": TEST_STOCK,
    "analysis_type": "full",
    "eval_mode": False,
    "eval_models": [],
    "raw_data": {},
    "agent_results": [],
    "evaluation_results": [],
    "messages": [],
    "summary": "",
    "final_verdict": "",
})

# Save structured output
output = {
    "stock_code": TEST_STOCK,
    "stock_name": TEST_NAME,
    "verdict": result.get("final_verdict", ""),
    "summary": result.get("summary", ""),
    "agents": []
}

for r in result.get("agent_results", []):
    output["agents"].append({
        "name": r["agent_name"],
        "confidence": r["confidence"],
        "analysis": r["analysis"],
        "length": len(r["analysis"]),
    })

out_path = os.path.join(os.path.dirname(__file__), "full_result.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Saved to {out_path}")
print(f"Agents: {len(output['agents'])}, Verdict: {output['verdict']}, Summary: {len(output['summary'])} chars")

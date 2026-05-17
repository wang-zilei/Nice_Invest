# -*- coding: utf-8 -*-
"""Quick smoke test: verify all 5 agents can initialize and run. """
import os, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ["OPENAI_API_KEY"] = "sk-32269f37bea144319b840742566b3475"
os.environ["DEEPSEEK_API_KEY"] = "sk-32269f37bea144319b840742566b3475"
os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"
os.environ["DEFAULT_MODEL"] = "deepseek-chat"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import run_agent_react

state = {
    "stock_code": "002594.SZ",
    "analysis_type": "full",
    "eval_mode": False,
    "eval_models": [],
    "raw_data": {},
    "agent_results": [],
    "evaluation_results": [],
    "messages": [],
    "summary": "",
    "final_verdict": "",
}

agents = ["fundamental", "technical", "valuation", "news"]

for agent_type in agents:
    print(f"Testing {agent_type}...", end=" ", flush=True)
    try:
        start = time.time()
        result = run_agent_react(agent_type, state)
        elapsed = round(time.time() - start, 1)
        print(f"PASS ({elapsed}s, {len(result)} chars)")
    except Exception as e:
        print(f"FAIL: {e}")

print("\nAll agent init tests done.")

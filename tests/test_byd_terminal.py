# -*- coding: utf-8 -*-
"""
Terminal test: BYD 002594.SZ analysis with Demo API Key
Verify whether the API itself works (distinguish API issue vs backend code issue).
"""
import os
import sys
import time
import io

# Fix Windows GBK stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Set API Key (using Demo Key from config.py)
os.environ["OPENAI_API_KEY"] = "sk-32269f37bea144319b840742566b3475"
os.environ["DEEPSEEK_API_KEY"] = "sk-32269f37bea144319b840742566b3475"
os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"
os.environ["DEFAULT_MODEL"] = "deepseek-chat"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI

print("=" * 60)
print("Test 1: LLM Direct Connection (DeepSeek API)")
print("=" * 60)

try:
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key="sk-32269f37bea144319b840742566b3475",
        base_url="https://api.deepseek.com",
        temperature=0,
        max_tokens=20,
        request_timeout=30,
        max_retries=1,
    )
    resp = llm.invoke([{"role": "user", "content": "Reply OK only"}])
    print(f"[PASS] LLM direct connection OK: {resp.content}")
except Exception as e:
    print(f"[FAIL] LLM direct connection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("Test 2: Agent Run (Fundamental Agent, BYD 002594.SZ)")
print("=" * 60)

try:
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

    start = time.time()
    result = run_agent_react("fundamental", state)
    elapsed = round(time.time() - start, 1)

    print(f"[PASS] Fundamental Agent OK (elapsed {elapsed}s)")
    print(f"--- First 800 chars ---")
    print(result[:800])

except Exception as e:
    print(f"[FAIL] Agent execution failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("Test 3: Check Demo API Key balance")
print("=" * 60)

try:
    llm2 = ChatOpenAI(
        model="deepseek-chat",
        api_key="sk-32269f37bea144319b840742566b3475",
        base_url="https://api.deepseek.com",
        temperature=0,
        max_tokens=5,
        request_timeout=30,
        max_retries=1,
    )
    resp2 = llm2.invoke([{"role": "user", "content": "Say hi"}])
    print(f"[PASS] Balance OK: {resp2.content}")
except Exception as e:
    error_msg = str(e)
    if "402" in error_msg or "Insufficient" in error_msg:
        print(f"[FAIL] Insufficient Balance (402): {e}")
    elif "401" in error_msg:
        print(f"[FAIL] Invalid Key (401): {e}")
    else:
        print(f"[WARN] Other error: {e}")

print()
print("=" * 60)
print("Test Complete")
print("=" * 60)

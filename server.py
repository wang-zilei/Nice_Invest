"""
server.py — FastAPI 后端入口
提供 REST API + SSE 流式推送，连接 React 前端与 LangGraph 分析引擎。

端点：
  GET  /api/health             健康检查
  POST /api/auth/send-code     发送邮箱验证码（Resend API）
  POST /api/auth/verify-code   校验验证码，返回 session_token
  GET  /api/auth/session       校验 session 有效性
  GET  /api/auth/usage         查询用户剩余免费次数
  POST /api/search             股票搜索（Top-5 匹配，基于 A 股注册表 ~5500 只）
  POST /api/validate-stock     校验用户输入是否为有效 A 股（安全护栏，含 LLM 兜底）
  POST /api/analyze            股票分析（SSE 流式，需 session）
  GET  /api/history            历史分析记录
  POST /api/config/validate    校验 API Key 有效性
"""
import json
import uuid
import time
import asyncio
import os
from typing import Optional, AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.logger import logger, print_startup_summary
from src.auth import (
    code_store, session_store, user_store,
    generate_code, send_verification_email,
)
from src.stock_registry import search_registry, validate_stock, get_registry_stats

# ============================================================
# FastAPI App
# ============================================================
app = FastAPI(title="Nice Invest API", version="0.2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Pydantic Models
# ============================================================
class SearchRequest(BaseModel):
    keyword: str
    tushare_token: Optional[str] = None

ANALYSIS_TIMEOUT = 300  # 整体分析超时（秒），覆盖 4 Agent + Summary

class AnalyzeRequest(BaseModel):
    stock_code: str                      # 如 "000001.SZ"
    stock_name: str = ""                 # 股票名称，如 "比亚迪"
    analysis_type: str = "full"          # full | fundamental | technical | valuation | news
    llm_config: dict = {}                # {model, openai_api_key, openai_base_url, ...}
    tushare_token: Optional[str] = None
    session_token: Optional[str] = None  # 用户 session token（前端 localStorage）

class ConfigValidateRequest(BaseModel):
    model: str = "deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


# ============================================================
# Auth 相关 Pydantic Models
# ============================================================
class SendCodeRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


class SessionCheckRequest(BaseModel):
    session_token: str

# ============================================================
# In-memory storage（面试项目，不做持久化）
# ============================================================
analysis_history: list = []

# ============================================================
# Health
# ============================================================
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.2.1"}


# ============================================================
# Auth 端点
# ============================================================
@app.post("/api/auth/send-code")
async def send_code(req: SendCodeRequest):
    """发送邮箱验证码（Resend API，失败时降级为终端输出）"""
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="请输入有效的邮箱地址")

    code = generate_code()
    code_store.set(email, code)
    logger.info(f"[AUTH] 验证码已生成 → {email}（{code}）")

    sent = await send_verification_email(email, code)
    if sent:
        logger.info(f"[AUTH] 验证码邮件已发送 → {email}")
        return {"ok": True, "message": "验证码已发送到您的邮箱", "dev_code": code}
    else:
        # 降级：Resend 未配置或发送失败时在终端打印验证码
        logger.warning(f"[AUTH] Resend 邮件发送失败，降级为终端输出 → {email} (code={code})")
        return {
            "ok": True,
            "message": "验证码已发送（开发模式：请查看终端输出）",
            "fallback": True,
            "dev_code": code,
        }


@app.post("/api/auth/verify-code")
async def verify_code(req: VerifyCodeRequest):
    """校验验证码，返回 session_token"""
    email = req.email.strip().lower()
    code = req.code.strip()

    if not code_store.verify(email, code):
        logger.warning(f"[AUTH] 验证码校验失败 → {email}")
        raise HTTPException(status_code=401, detail="验证码错误或已过期")

    session_token = session_store.create(email)
    user_store.get_or_create(email)

    logger.info(f"[AUTH] 用户登录成功 → {email}")
    return {
        "ok": True,
        "session_token": session_token,
        "email": email,
    }


@app.get("/api/auth/session")
async def check_session(session_token: str = Header(None, alias="X-Session-Token")):
    """校验 session 有效性（游客模式 __guest__ 始终有效）"""
    if not session_token:
        return {"valid": False, "reason": "缺少 session_token"}
    if session_token == "__guest__":
        return {"valid": True, "email": "guest@niceinvest.dev", "is_guest": True}
    email = session_store.validate(session_token)
    if not email:
        return {"valid": False, "reason": "session 无效或已过期"}
    return {"valid": True, "email": email}


@app.get("/api/auth/usage")
async def get_usage(session_token: str = Header(None, alias="X-Session-Token")):
    """查询用户信息"""
    if not session_token:
        raise HTTPException(status_code=401, detail="缺少 session_token")
    if session_token == "__guest__":
        return {"email": "guest@niceinvest.dev", "is_guest": True}
    email = session_store.validate(session_token)
    if not email:
        raise HTTPException(status_code=401, detail="session 无效或已过期")
    return {"email": email}

# ============================================================
# POST /api/search — 股票搜索（基于 A 股注册表，覆盖全量 ~5500 只股票）
# ============================================================
@app.post("/api/search")
async def search_stocks(req: SearchRequest):
    keyword = (req.keyword or "").strip()
    if not keyword:
        return {"matches": []}

    try:
        results = search_registry(keyword, limit=5)
        matches = [{"ts_code": r["ts_code"], "name": r["name"], "industry": ""} for r in results]
        return {"matches": matches}
    except Exception as e:
        logger.warning(f"[search] 搜索异常: {e}")
        return {"matches": []}


# ============================================================
# POST /api/validate-stock — 校验用户输入是否为有效 A 股（安全护栏）
# ============================================================
class ValidateRequest(BaseModel):
    input: str


@app.post("/api/validate-stock")
async def validate_stock_input(req: ValidateRequest):
    user_input = (req.input or "").strip()
    if not user_input:
        return {"valid": False, "message": "请输入公司名称或股票代码"}

    # 第一层：本地注册表精确匹配
    match = validate_stock(user_input)
    if match:
        logger.info(f"[VALIDATE] 本地匹配成功 → {match['name']} ({match['ts_code']})")
        return {
            "valid": True,
            "ts_code": match["ts_code"],
            "name": match["name"],
            "source": "registry",
        }

    # 第二层：LLM 辅助识别（处理简称、别名等本地匹配不到的情况）
    try:
        llm_match = await _llm_validate_stock(user_input)
        if llm_match:
            logger.info(f"[VALIDATE] LLM 匹配成功 → {llm_match['name']} ({llm_match['ts_code']})")
            return {
                "valid": True,
                "ts_code": llm_match["ts_code"],
                "name": llm_match["name"],
                "source": "llm",
            }
    except Exception as e:
        logger.warning(f"[VALIDATE] LLM 校验异常: {e}")

    logger.info(f"[VALIDATE] 未识别 → \"{user_input}\"")
    return {
        "valid": False,
        "message": f"未识别到 \"{user_input}\" 为有效的 A 股公司。请检查公司名称或代码是否正确。示例：平安银行、000001.SZ",
    }


async def _llm_validate_stock(user_input: str) -> dict | None:
    """使用 LLM 识别用户输入的模糊公司名称/代码"""
    import os
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = os.environ.get("DEFAULT_MODEL", "deepseek-chat")

    prompt = f"""你是一个A股股票代码验证助手。用户输入了"{user_input}"，请判断这最可能是哪只A股。

规则：
- 如果输入是A股公司简称、全称、常见别名或股票代码，返回对应的公司全称和代码
- 代码格式为 Tushare 格式（如 000001.SZ、600519.SH）
- 如果输入显然不是任何已知的A股公司（如乱码、明显的外国公司、虚构名称），返回 null

只返回JSON，不要任何其他文字：
{{"name": "公司全称", "ts_code": "代码"}}
或
{{"name": null, "ts_code": null}}"""

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        max_tokens=100,
        request_timeout=8,
        max_retries=0,
    )
    resp = llm.invoke([{"role": "user", "content": prompt}])
    content = resp.content if hasattr(resp, "content") else str(resp)

    # 提取 JSON
    import re
    match_obj = re.search(r'\{[^}]+\}', content)
    if match_obj:
        try:
            data = json.loads(match_obj.group(0))
            if data.get("name") and data.get("ts_code"):
                # 二次确认：LLM 返回的代码在注册表中存在
                registry_match = validate_stock(data["ts_code"])
                if registry_match:
                    return registry_match
                # LLM 返回的代码不在注册表中，尝试用名称再匹配
                name_match = validate_stock(data["name"])
                if name_match:
                    return name_match
        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# POST /api/analyze — SSE 流式分析
# ============================================================
@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, raw_request: Request):
    stock_code = req.stock_code.strip()
    stock_name = req.stock_name.strip() or stock_code
    analysis_type = req.analysis_type.strip() or "full"

    if not stock_code:
        raise HTTPException(status_code=400, detail="stock_code 不能为空")

    # ---- Session 鉴权（游客模式：session_token="__guest__" 直接放行） ----
    user_email = None
    is_guest = False
    session_token = req.session_token
    if session_token == "__guest__":
        user_email = "guest@niceinvest.dev"
        is_guest = True
    elif session_token:
        user_email = session_store.validate(session_token)
    if not user_email:
        raise HTTPException(status_code=401, detail="请先登录后再使用分析功能")

    # ---- 检查 API Key：用户自备 > 后端体验 Key ----
    user_config = req.llm_config or {}
    user_has_own_key = bool(user_config.get("api_key") or user_config.get("openai_api_key"))

    # 生成分析 ID
    analysis_id = str(uuid.uuid4())[:8]
    logger.info(f"[ANALYZE] 开始 → {stock_code} | 用户={user_email} | 自备Key={user_has_own_key}")

    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 事件生成器（带超时保护，避免永久挂起）"""
        started_at = time.time()

        yield _sse("init", {"analysis_id": analysis_id, "stock_code": stock_code})

        try:
            # ---- 配置 LLM ----
            yield _sse("progress", {"agent": "system", "message": "正在初始化分析环境...", "step": "config"})

            llm_config = req.llm_config or {}
            _apply_llm_config(llm_config, user_email=user_email)

            # ---- 预检：快速验证 LLM 连通性 ----
            yield _sse("progress", {"agent": "system", "message": "正在验证大模型连接...", "step": "preflight"})
            preflight_ok, preflight_msg = await _preflight_check()
            if not preflight_ok:
                yield _sse("error", {
                    "message": f"大模型连接失败：{preflight_msg}\n\n请检查 API Key 和 Base URL 是否正确配置。点击右上角齿轮图标进入配置页面。"
                })
                return
            yield _sse("progress", {"agent": "system", "message": f"大模型连接正常（{preflight_msg}）", "step": "preflight_done"})

            # ---- Router 阶段 ----
            yield _sse("progress", {"agent": "router", "message": "正在解析股票代码...", "step": "router_start"})

            from src.state import AnalysisState

            # 确定要执行的 Agent 列表
            agent_map = {
                "full": ["fundamental", "technical", "valuation", "news"],
                "fundamental": ["fundamental"],
                "technical": ["technical"],
                "valuation": ["valuation"],
                "news": ["news"],
            }
            agents_to_run = agent_map.get(analysis_type, ["fundamental", "technical", "valuation", "news"])

            agent_names_cn = {
                "fundamental": "基本面", "technical": "技术面",
                "valuation": "估值", "news": "新闻舆情"
            }

            yield _sse("router_done", {
                "agents": agents_to_run,
                "stock_code": stock_code,
            })

            # 检查客户端是否已断开
            if await raw_request.is_disconnected():
                return

            # ---- 并行执行 Agent（asyncio.gather，带超时） ----
            yield _sse("progress", {"agent": "system", "message": f"开始并行执行 {len(agents_to_run)} 个分析Agent...", "step": "agents_start"})

            from src.graph import run_agent_react, AGENT_TIMEOUT

            # 先发送所有 agent_start 事件
            for agent_type in agents_to_run:
                cn_name = agent_names_cn.get(agent_type, agent_type)
                yield _sse("agent_start", {"agent": agent_type, "name": cn_name})

            # 构建每个 Agent 的共享状态
            shared_state = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "analysis_type": analysis_type,
                "eval_mode": False,
                "eval_models": [],
                "raw_data": {},
                "agent_results": [],
                "evaluation_results": [],
                "messages": [],
                "summary": "",
                "final_verdict": "",
            }

            # 并行调度所有 Agent
            async def _run_single_agent(agent_type: str) -> dict:
                """在 executor 中运行单个 Agent，返回结果字典"""
                cn_name = agent_names_cn.get(agent_type, agent_type)
                loop = asyncio.get_event_loop()
                try:
                    result_text = await asyncio.wait_for(
                        loop.run_in_executor(None, run_agent_react, agent_type, shared_state),
                        timeout=AGENT_TIMEOUT + 10,
                    )

                    confidence = 0.8
                    if any(kw in str(result_text) for kw in ["数据充分", "信息完整", "指标清晰"]):
                        confidence = 0.85
                    elif any(kw in str(result_text) for kw in ["数据不足", "信息有限", "缺乏"]):
                        confidence = 0.65

                    result_text_str = str(result_text)
                    cleaned_text = _clean_agent_output(result_text_str)
                    json_data = _extract_json_from_text(result_text_str)

                    # preview: 取清洗后文本的前 400 字符，截断在完整句子边界
                    preview = cleaned_text[:400]
                    last_period = max(preview.rfind('。'), preview.rfind('\n'))
                    if last_period > 200:
                        preview = preview[:last_period + 1]

                    return {
                        "status": "ok",
                        "agent_type": agent_type,
                        "agent_name": cn_name,
                        "analysis": cleaned_text,
                        "confidence": confidence,
                        "json_data": json_data,
                        "preview": preview,
                    }

                except asyncio.TimeoutError:
                    logger.error(f"[AGENT] {cn_name} Agent 执行超时（{AGENT_TIMEOUT + 10}s）")
                    return {
                        "status": "timeout",
                        "agent_type": agent_type,
                        "agent_name": cn_name,
                        "error": f"{cn_name} Agent 执行超时（{AGENT_TIMEOUT + 10}秒），请检查 API 连接。点击右上角齿轮图标查看配置。",
                    }

                except Exception as e:
                    logger.error(f"[AGENT] {cn_name} Agent 执行异常: {e}")
                    return {
                        "status": "error",
                        "agent_type": agent_type,
                        "agent_name": cn_name,
                        "error": str(e),
                    }

            # 并行执行 + 保持原始顺序
            tasks = [_run_single_agent(at) for at in agents_to_run]
            completed = await asyncio.gather(*tasks)

            # 收集结果并推送 SSE
            agent_results = []
            for result in completed:
                if result["status"] == "ok":
                    agent_results.append({
                        "agent_name": result["agent_name"],
                        "analysis": result["analysis"],
                        "confidence": result["confidence"],
                    })
                    yield _sse("agent_complete", {
                        "agent": result["agent_type"],
                        "name": result["agent_name"],
                        "confidence": result["confidence"],
                        "json_data": result["json_data"],
                        "preview": result["preview"],
                        "analysis": result["analysis"],
                    })
                else:
                    agent_results.append({
                        "agent_name": result["agent_name"],
                        "analysis": f"分析{'超时' if result['status'] == 'timeout' else '异常'}: {result['error']}",
                        "confidence": 0.0,
                    })
                    yield _sse("agent_error", {
                        "agent": result["agent_type"],
                        "name": result["agent_name"],
                        "error": result["error"],
                    })

            # 检查客户端是否已断开
            if await raw_request.is_disconnected():
                return

            # ---- Summary 汇总（直接调用 summary_node，避免 graph.invoke 重复执行 Agent） ----
            yield _sse("progress", {"agent": "summary", "message": "开始汇总分析结果...", "step": "summary_start"})
            yield _sse("agent_start", {"agent": "summary", "name": "综合汇总"})

            from src.graph import summary_node

            summary_state = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "analysis_type": analysis_type,
                "eval_mode": False,
                "eval_models": [],
                "raw_data": {},
                "agent_results": agent_results,
                "evaluation_results": [],
                "messages": [],
                "summary": "",
                "final_verdict": "",
            }

            try:
                loop_obj = asyncio.get_event_loop()
                result_state = await asyncio.wait_for(
                    loop_obj.run_in_executor(None, summary_node, summary_state),
                    timeout=AGENT_TIMEOUT + 10,
                )
                summary_text = result_state.get("summary", "") if isinstance(result_state, dict) else str(result_state)
                final_verdict = result_state.get("final_verdict", "中性") if isinstance(result_state, dict) else "中性"

                # 清洗 summary 输出
                summary_text = _clean_agent_output(str(summary_text))

            except asyncio.TimeoutError:
                logger.warning(f"[SUMMARY] 汇总 Agent 执行超时，降级为原始结果拼接")
                parts = [f"【{r['agent_name']}】\n{_clean_agent_output(r['analysis'])}" for r in agent_results]
                summary_text = "## 综合汇总（汇总超时，以下为各 Agent 原始结果）\n\n" + "\n\n---\n\n".join(parts)
                final_verdict = "数据不足"
                yield _sse("agent_error", {
                    "agent": "summary",
                    "name": "综合汇总",
                    "error": "汇总 Agent 执行超时，已降级为原始结果拼接",
                })

            except Exception as e:
                logger.error(f"[SUMMARY] 汇总 Agent 执行异常: {e}")
                parts = [f"【{r['agent_name']}】\n{_clean_agent_output(r['analysis'])}" for r in agent_results]
                summary_text = f"## 综合汇总（汇总异常）\n\n异常: {str(e)}\n\n" + "\n\n---\n\n".join(parts)
                final_verdict = "数据不足"
                yield _sse("agent_error", {
                    "agent": "summary",
                    "name": "综合汇总",
                    "error": str(e),
                })

            summary_json = _extract_json_from_text(str(summary_text))

            yield _sse("agent_complete", {
                "agent": "summary",
                "name": "综合汇总",
                "verdict": final_verdict,
                "json_data": summary_json,
                "analysis": summary_text,
                "preview": summary_text[:400] if summary_text else "",
            })

            # ---- 完成 ----
            elapsed = round(time.time() - started_at, 1)

            logger.info(f"[ANALYZE] 完成 → {stock_code} | 耗时={elapsed}s | 判定={final_verdict}")

            # 构建完整历史记录（包含所有分析结果，供历史回放）
            full_record = {
                "id": analysis_id,
                "stock_code": stock_code,
                "stock_name": stock_name,
                "analysis_type": analysis_type,
                "verdict": final_verdict,
                "elapsed": elapsed,
                "created_at": datetime.now().isoformat(),
                "agent_results": agent_results,
                "summary_text": summary_text,
                "summary_json": summary_json,
            }
            analysis_history.insert(0, full_record)
            if len(analysis_history) > 50:
                analysis_history.pop()

            yield _sse("done", {
                "analysis_id": analysis_id,
                "stock_name": stock_name,
                "verdict": final_verdict,
                "elapsed": elapsed,
                "summary_json": summary_json,
            })

        except asyncio.CancelledError:
            logger.warning(f"[ANALYZE] 取消 → {stock_code}")
            yield _sse("error", {"message": "分析已被取消"})
        except Exception as e:
            logger.error(f"[ANALYZE] 异常 → {stock_code}: {e}")
            yield _sse("error", {"message": f"分析异常: {str(e)}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# GET /api/history — 历史分析记录列表
# ============================================================
@app.get("/api/history")
async def get_history(limit: int = 20):
    # 只返回列表需要的轻量字段
    light_history = []
    for h in analysis_history[:limit]:
        light_history.append({
            "id": h.get("id"),
            "stock_code": h.get("stock_code"),
            "stock_name": h.get("stock_name", h.get("stock_code")),
            "analysis_type": h.get("analysis_type"),
            "verdict": h.get("verdict"),
            "elapsed": h.get("elapsed"),
            "created_at": h.get("created_at"),
        })
    return {"history": light_history}


# ============================================================
# GET /api/history/{analysis_id} — 获取单条历史记录的完整结果
# ============================================================
@app.get("/api/history/{analysis_id}")
async def get_history_detail(analysis_id: str):
    for h in analysis_history:
        if h.get("id") == analysis_id:
            return {"found": True, "record": h}
    return {"found": False, "record": None}


# ============================================================
# POST /api/config/validate — 校验 API Key
# ============================================================
@app.post("/api/config/validate")
async def validate_config(req: ConfigValidateRequest):
    results = {}

    # 校验 LLM API key（含超时保护，避免前端"测试连接"永久阻塞）
    if req.api_key and req.model:
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=req.model,
                api_key=req.api_key,
                base_url=req.base_url or "https://api.deepseek.com/v1",
                temperature=0,
                max_tokens=5,
                request_timeout=10,
                max_retries=0,
            )
            loop_obj = asyncio.get_event_loop()
            resp = await asyncio.wait_for(
                loop_obj.run_in_executor(None, llm.invoke, [{"role": "user", "content": "Hi"}]),
                timeout=12,
            )
            if resp and hasattr(resp, "content"):
                results["llm"] = "valid"
                logger.info(f"[VALIDATE] 连接成功 → model={req.model}")
            else:
                results["llm"] = "error: 模型返回异常"
        except asyncio.TimeoutError:
            results["llm"] = "连接超时（12秒），请检查 Base URL 地址是否正确、网络是否可达"
            logger.warning(f"[VALIDATE] 超时 → model={req.model}")
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg.lower():
                results["llm"] = "API Key 无效（401），请检查 Key 是否正确"
            elif "402" in error_msg or "Insufficient" in error_msg:
                results["llm"] = "API 账户余额不足（402）"
            elif "403" in error_msg:
                results["llm"] = "API 访问被拒绝（403），请检查账户权限"
            elif "429" in error_msg:
                results["llm"] = "API 请求频率过高（429），请稍后重试"
            elif "404" in error_msg:
                results["llm"] = "API 端点不存在（404），请检查 Base URL 地址"
            elif "Connection" in error_msg or "connect" in error_msg.lower():
                results["llm"] = "无法连接到 API 服务器，请检查 Base URL 和网络"
            else:
                results["llm"] = f"连接失败: {error_msg[:120]}"
            logger.warning(f"[VALIDATE] 失败 → model={req.model}: {results['llm']}")
    else:
        results["llm"] = "not_provided"

    return {"results": results}


# ============================================================
# 辅助函数
# ============================================================
async def _preflight_check() -> tuple:
    """预检 LLM 连通性，返回 (ok: bool, message: str)"""
    try:
        from langchain_openai import ChatOpenAI
        import os

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        model = os.environ.get("DEFAULT_MODEL", "deepseek-chat")

        if not api_key:
            return False, "未配置 API Key，请点击右上角齿轮图标配置您的大模型 API"

        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0,
            max_tokens=5,
            request_timeout=10,
            max_retries=0,
        )
        loop = asyncio.get_event_loop()
        resp = await asyncio.wait_for(
            loop.run_in_executor(None, llm.invoke, [{"role": "user", "content": "Hi"}]),
            timeout=12,
        )
        if resp and hasattr(resp, "content"):
            return True, f"模型 {model} 连接正常"
        return False, f"模型 {model} 返回异常，请检查 API 配置"
    except asyncio.TimeoutError:
        return False, "连接超时（12秒），请检查 Base URL 地址是否正确、网络是否可达"
    except Exception as e:
        error_msg = str(e)
        # 按优先级匹配常见错误
        if "402" in error_msg or "Insufficient Balance" in error_msg or "insufficient" in error_msg.lower():
            return False, "API 账户余额不足（402）。体验 Key 余额已用尽，请点击右上角齿轮图标配置您自己的 API Key"
        if "401" in error_msg or "Unauthorized" in error_msg or "unauthorized" in error_msg.lower():
            return False, "API Key 无效（401），请检查 Key 是否正确、是否已过期"
        if "403" in error_msg or "Forbidden" in error_msg or "forbidden" in error_msg.lower():
            return False, "API 访问被拒绝（403），请检查账户权限或余额是否充足"
        if "429" in error_msg or "Rate" in error_msg:
            return False, "API 请求频率过高（429），请稍后重试"
        if "404" in error_msg:
            return False, "API 端点不存在（404），请检查 Base URL 地址是否正确"
        if "Connection" in error_msg or "connect" in error_msg.lower():
            return False, f"无法连接到 API 服务器，请检查 Base URL 地址和网络连接"
        # 兜底：返回原始错误（截断长度）
        return False, error_msg[:150]


def _apply_llm_config(llm_config: dict, user_email: str = None):
    """将 LLM 配置写入环境变量。用户自备 Key 优先，否则使用后端体验 Key。

    体验 Key 读取优先级：环境变量 DEMO_API_KEY → config.py 兜底
    关键：必须同时设置所有模型族的环境变量（OPENAI/DEEPSEEK/QWEN），
    因为 get_llm() 中不同模型分支读取各自的 env var。
    漏设任何一个 base_url 都会导致 Agent 执行失败。
    """
    api_key = llm_config.get("api_key") or llm_config.get("openai_api_key")
    base_url = llm_config.get("base_url") or llm_config.get("openai_base_url")
    model = llm_config.get("model", "deepseek-chat")

    # 体验 Key 从 config.py 兜底（本地开发时环境变量通常不设）
    try:
        from config import DEMO_API_KEY as _CFG_DEMO_KEY, DEMO_BASE_URL as _CFG_DEMO_URL
    except ImportError:
        _CFG_DEMO_KEY = ""
        _CFG_DEMO_URL = ""

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["DEEPSEEK_API_KEY"] = api_key
        os.environ["QWEN_API_KEY"] = api_key
        logger.info(f"[CONFIG] 使用用户自备 Key → model={model}")
    else:
        demo_key = os.environ.get("DEMO_API_KEY", "") or _CFG_DEMO_KEY
        os.environ["OPENAI_API_KEY"] = demo_key
        os.environ["DEEPSEEK_API_KEY"] = demo_key
        os.environ["QWEN_API_KEY"] = demo_key
        logger.info(f"[CONFIG] 使用体验 Key → model={model}")

    if base_url:
        os.environ["OPENAI_BASE_URL"] = base_url
        os.environ["DEEPSEEK_BASE_URL"] = base_url
        os.environ["QWEN_BASE_URL"] = base_url
    else:
        default_url = os.environ.get("DEMO_BASE_URL", "") or _CFG_DEMO_URL or "https://api.deepseek.com/v1"
        os.environ["OPENAI_BASE_URL"] = default_url
        os.environ["DEEPSEEK_BASE_URL"] = default_url
        os.environ["QWEN_BASE_URL"] = default_url
    os.environ["DEFAULT_MODEL"] = model


def _sse(event: str, data: dict) -> str:
    """格式化为 SSE 消息"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_json_from_text(text: str) -> Optional[dict]:
    """从 Markdown 文本中提取第一个 JSON 代码块"""
    if not text:
        return None
    # 尝试找到 ```json ... ``` 代码块
    import re
    match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # 兜底：尝试找 { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _clean_agent_output(text: str) -> str:
    """清洗 Agent 输出，去除思考过程、过渡语等非报告内容

    主要处理 DeepSeek 等模型在输出中混入的推理链/思考过程。
    """
    if not text:
        return text
    import re

    # 1. 去除 DeepSeek 思考块（思考... 思考）
    text = re.sub(r'思考[\s\S]*?思考', '', text)
    # 2. 去除 <｜end▁of▁thinking｜>...  标签残留
    text = re.sub(r'响应[\s\S]*?响应', '', text)
    # 3. 去除常见的过渡/思考句式开头的行
    thinking_patterns = [
        r'^(好的[，,].*$)',           # "好的，数据已获取..."
        r'^(现在我来.*$)',            # "现在我来分析..."
        r'^(下面给出.*$)',            # "下面给出..."
        r'^(让我.*$)',               # "让我整合..."
        r'^(我手动.*$)',              # "我手动计算..."
        r'^(看起来.*$)',              # "看起来..."
        r'^(根据获取.*$)',            # "根据获取的数据..."
        r'^(首先[，,].*$)',           # "首先，..."
        r'^(接下来.*$)',              # "接下来..."
        r'^(最后[，,].*$)',           # "最后，..."
        r'^(基于以上.*$)',            # "基于以上..."
        r'^(我们已经.*$)',            # "我们已经..."
    ]
    for pattern in thinking_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)

    # 4. 去除 Markdown 水平分隔线
    text = re.sub(r'^[\-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # 5. 去除 Markdown 标题标记符（保留标题文字），先处理 ### 再 ## 再 #
    text = re.sub(r'^###\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+', '', text, flags=re.MULTILINE)

    # 6. 去除 Markdown 粗体/斜体标记符（保留内部文字）
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)

    # 7. 清理多余的空行（3个以上连续空行合并为2个）
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # 8. 去除开头的空行
    text = text.lstrip('\n')

    return text.strip()


# ============================================================
# 静态文件 serve（前端 SPA，所有 API 路由优先匹配后才 fallback 到此）
# ============================================================
import os as _os
_frontend_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "web", "dist")
if _os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="static")
    logger.info(f"前端静态文件已挂载: {_frontend_dir}")
else:
    logger.warning(f"前端静态文件目录不存在: {_frontend_dir}，请先执行 cd web && npm run build")


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print_startup_summary()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

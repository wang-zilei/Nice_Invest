"""
stock_registry.py — A股公司注册表（akshare → JSON 缓存）

基于 akshare stock_info_a_code_name() 获取全量 A 股列表（~5500 只），
缓存到 data/a_share_registry.json，每日自动刷新。

用于：搜索建议 + 输入合法性校验（安全护栏）
"""
import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

_CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_FILE = _CACHE_DIR / "a_share_registry.json"
_CACHE_MAX_AGE = 86400  # 24 小时

_registry = None


# ============================================================
# 代码格式转换
# ============================================================

def _code_to_ts_code(code: str) -> str:
    """将纯数字代码转为 Tushare 格式（如 000001 → 000001.SZ）"""
    code = code.strip().zfill(6)
    # 上海交易所
    if code.startswith(("60", "68")):
        return f"{code}.SH"
    # 北京交易所
    if code.startswith(("43", "83", "87", "92")):
        return f"{code}.BJ"
    # 深圳交易所（00xxxx, 002xxx, 003xxx, 30xxxx, 20xxxx）
    return f"{code}.SZ"


def _ts_code_to_pure(ts_code: str) -> str:
    """将 Tushare 格式代码转为纯数字（如 000001.SZ → 000001）"""
    return ts_code.split(".")[0] if "." in ts_code else ts_code


# ============================================================
# Registry 加载与缓存
# ============================================================

def _fetch_from_akshare() -> list[dict]:
    """从 akshare 获取全量 A 股列表（代码+名称）"""
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        if df is None or df.empty:
            raise RuntimeError("akshare 返回空数据")
        results = []
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip().zfill(6)
            name = str(row.get("name", "")).strip()
            if not code or not name or len(code) != 6:
                continue
            results.append({
                "code": code,
                "name": name,
                "ts_code": _code_to_ts_code(code),
            })
        return results
    except ImportError:
        raise RuntimeError("akshare 未安装，请执行: pip install akshare")
    except Exception as e:
        raise RuntimeError(f"akshare 获取 A 股列表失败: {str(e)}")


def _load_from_cache() -> list[dict] | None:
    """从缓存文件加载，有效期内返回数据，否则返回 None"""
    if not _CACHE_FILE.exists():
        return None
    try:
        mtime = _CACHE_FILE.stat().st_mtime
        if time.time() - mtime > _CACHE_MAX_AGE:
            return None  # 缓存过期
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 1000:
            return data
        return None
    except Exception:
        return None


def _save_to_cache(data: list[dict]):
    """保存 registry 到缓存文件"""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    # 同时写 .gitkeep 确保目录被 git 追踪（如果尚不存在）
    gitkeep = _CACHE_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


def load_registry(force_refresh: bool = False) -> list[dict]:
    """加载 A 股注册表（优先缓存，缓存过期或强制刷新时从 akshare 拉取）

    返回 list[dict]，每个元素含 code / name / ts_code
    """
    global _registry

    if _registry is not None and not force_refresh:
        return _registry

    # 尝试从缓存加载
    if not force_refresh:
        cached = _load_from_cache()
        if cached is not None:
            _registry = cached
            return _registry

    # 缓存不可用，从 akshare 拉取
    try:
        data = _fetch_from_akshare()
        _save_to_cache(data)
        _registry = data
        return _registry
    except Exception:
        # akshare 也失败时，尝试用过期的缓存兜底
        cached_stale = _load_from_cache() if _CACHE_FILE.exists() else None
        # 前面 _load_from_cache 已经检查了过期，但在这里强制重新加载（忽略过期）
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                cached_stale = json.load(f)
                if isinstance(cached_stale, list) and len(cached_stale) > 1000:
                    _registry = cached_stale
                    return _registry
        except Exception:
            pass
        raise RuntimeError(
            "无法加载A股公司列表：akshare 获取失败且无有效缓存。"
            "请检查网络连接后重启服务。"
        )


# ============================================================
# 搜索与校验
# ============================================================

def search_registry(keyword: str, limit: int = 5) -> list[dict]:
    """模糊搜索 A 股注册表

    搜索优先级：代码精确匹配 > 名称精确匹配 > 名称包含 > 代码包含
    """
    registry = load_registry()
    kw = keyword.strip()
    if not kw:
        return []

    results = []
    kw_lower = kw.lower()

    for stock in registry:
        code = stock["code"]
        name = stock["name"]
        ts_code = stock["ts_code"]

        # 精确匹配权重最高
        if code == kw or ts_code == kw or ts_code.lower() == kw_lower:
            results.append((0, stock))
        elif name == kw:
            results.append((1, stock))
        elif kw in name or kw_lower in name.lower():
            results.append((2, stock))
        elif kw in code or kw in ts_code:
            results.append((3, stock))

    # 按优先级排序，取 top-N
    results.sort(key=lambda x: x[0])
    return [r[1] for r in results[:limit]]


def validate_stock(input_str: str) -> dict | None:
    """校验用户输入是否为有效 A 股公司

    返回: {code, name, ts_code} 或 None
    """
    input_str = input_str.strip()
    if not input_str:
        return None

    registry = load_registry()
    input_lower = input_str.lower()

    # 1. 精确匹配 ts_code（如 "000001.SZ"、"000001"）
    for s in registry:
        if s["code"] == input_str or s["ts_code"] == input_str or s["ts_code"].lower() == input_lower:
            return s

    # 2. 精确匹配名称
    for s in registry:
        if s["name"] == input_str:
            return s

    # 3. 模糊名称匹配（取第一个包含关键词的，最优匹配）
    best = None
    for s in registry:
        if input_str in s["name"]:
            if best is None or len(s["name"]) < len(best["name"]):
                best = s

    return best


def get_registry_stats() -> dict:
    """获取注册表统计信息"""
    registry = load_registry()
    sh_count = sum(1 for s in registry if s["ts_code"].endswith(".SH"))
    sz_count = sum(1 for s in registry if s["ts_code"].endswith(".SZ"))
    bj_count = sum(1 for s in registry if s["ts_code"].endswith(".BJ"))
    return {
        "total": len(registry),
        "shanghai": sh_count,
        "shenzhen": sz_count,
        "beijing": bj_count,
        "cache_file": str(_CACHE_FILE),
        "cache_exists": _CACHE_FILE.exists(),
    }

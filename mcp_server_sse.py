"""
mcp_server_sse.py — 独立进程 FastMCP Server（SSE 传输）

与 mcp_server_embedded.py 工具定义完全相同，但传输方式不同：
- Embedded: 同一进程，通过 stdin/stdout 管道通信
- SSE: 独立进程，通过 HTTP Server-Sent Events 通信

运行方式：
    python mcp_server_sse.py
启动后监听 http://127.0.0.1:8765，Agent 通过 SSE 连接。

MCP 优势：
- 服务器和客户端可以完全独立部署在不同机器上
- 可以用任何语言实现服务器（TypeScript、Go、Rust 等）
- 多个 Agent 可以同时连接同一个 MCP Server
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="financial-tools-sse",
    instructions="金融分析工具 MCP Server（独立进程，SSE 传输）",
    host="127.0.0.1",
    port=8765,
)


# ============================================================
# MCP 工具定义（与嵌入式版本完全相同）
# ============================================================

@mcp.tool()
def get_stock_info_mcp(ts_code: str) -> str:
    """获取股票基本信息和估值快照（Tushare Pro）。
    参数 ts_code: 股票代码，如 "600519.SH"
    返回: 名称、行业、市值、PE/PB/PS 等估值指标
    """
    from src.mcp_tools.tushare_api import get_stock_basic
    return get_stock_basic(ts_code)


@mcp.tool()
def get_stock_info_yahoo_mcp(ts_code: str) -> str:
    """获取 Yahoo Finance 股票信息和估值快照（海外兜底）。
    参数 ts_code: 股票代码，如 "600519.SH"（自动转为 .SS 格式）
    返回: 名称、行业、PE/PB/PS/PEG/股息率/ROE 等
    """
    from src.mcp_tools.yahoo_api import get_stock_info_yahoo
    return get_stock_info_yahoo(ts_code)


@mcp.tool()
def calc_financial_ratio_mcp(
    current_assets: float,
    current_liabilities: float,
    quick_assets: float = None,
    total_debt: float = None,
    total_assets: float = None
) -> str:
    """计算财务比率：流动比率、速动比率、资产负债率。
    参数:
        current_assets: 流动资产
        current_liabilities: 流动负债
        quick_assets: 速动资产（可选）
        total_debt: 总负债（可选）
        total_assets: 总资产（可选）
    返回: JSON 格式的财务比率结果
    """
    from src.mcp_tools.calculator import calc_financial_ratio
    result = calc_financial_ratio(
        current_assets, current_liabilities,
        quick_assets, total_debt, total_assets
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.resource(
    uri="stock://registry/a_shares",
    name="A股注册表",
    description="全部 A 股上市公司的股票代码和名称列表",
    mime_type="application/json",
)
def get_stock_registry() -> str:
    """读取 A 股注册表——全部 ~5500 只股票的代码和名称列表。"""
    registry_path = os.path.join(os.path.dirname(__file__), "data", "a_share_registry.json")
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            sample = data[:100]
            return json.dumps({"total": len(data), "showing": 100, "stocks": sample}, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False, indent=2)[:8000]
    return json.dumps({"error": "注册表文件不存在", "path": registry_path}, ensure_ascii=False)


@mcp.tool()
def get_server_info() -> str:
    """获取 MCP Server 元信息：可用工具列表、数据源、版本等。"""
    return json.dumps({
        "server_name": "financial-tools-sse",
        "transport": "sse",
        "url": "http://127.0.0.1:8765",
        "available_tools": [
            "get_stock_info_mcp",
            "get_stock_info_yahoo_mcp",
            "calc_financial_ratio_mcp",
            "get_server_info"
        ],
        "available_resources": [
            "stock://registry/a_shares"
        ],
        "data_sources": ["Tushare Pro", "Yahoo Finance"],
        "note": "这是独立进程 SSE 模式，服务器和客户端可以部署在不同机器上。",
    }, ensure_ascii=False, indent=2)


# ============================================================
# 启动入口（SSE 模式，独立进程）
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Server (SSE 模式) 启动中...")
    print("监听地址: http://127.0.0.1:8765")
    print("Agent 连接 URL: http://127.0.0.1:8765/sse")
    print("=" * 60)
    mcp.run(transport="sse")

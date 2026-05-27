"""
mcp_server_embedded.py — 嵌入式 FastMCP Server（stdio 传输）

这个文件是一个真正的 MCP Server，运行在同一进程中，通过 stdin/stdout 管道通信。
展示了 MCP 协议的核心能力：
1. @mcp.tool() 注册工具（对比 Function Call 的硬编码导入）
2. @mcp.resource() 暴露静态数据（Function Call 没有对应能力）
3. 工具动态发现（运行时自动获取可用工具列表）

运行方式：作为子进程由 mcp_loader.py 启动（stdio 模式）
"""
import sys
import os
import json

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="financial-tools-embedded",
    instructions="金融分析工具 MCP Server（嵌入式，stdio 传输）",
)


# ============================================================
# MCP 工具定义（对比 Function Call：不需要 @tool 装饰器 + bind_tools）
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


# ============================================================
# MCP Resource（Function Call 没有的能力：暴露静态数据）
# ============================================================

@mcp.resource(
    uri="stock://registry/a_shares",
    name="A股注册表",
    description="全部 A 股上市公司的股票代码和名称列表",
    mime_type="application/json",
)
def get_stock_registry() -> str:
    """读取 A 股注册表——全部 ~5500 只股票的代码和名称。

    MCP 优势说明：
    Resource 是 MCP 协议特有的能力，允许 Server 暴露静态或半静态数据。
    Function Call 只能"调用函数"，而 MCP 的 Agent 还可以"读取资源"。
    """
    registry_path = os.path.join(os.path.dirname(__file__), "data", "a_share_registry.json")
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 取前 100 只作为示例，避免截断破坏 JSON 结构
        if isinstance(data, list):
            sample = data[:100]
            return json.dumps({"total": len(data), "showing": 100, "stocks": sample}, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False, indent=2)[:8000]
    return json.dumps({"error": "注册表文件不存在", "path": registry_path}, ensure_ascii=False)


# ============================================================
# 动态发现工具（展示 MCP 运行时工具发现能力）
# ============================================================

@mcp.tool()
def get_server_info() -> str:
    """获取 MCP Server 元信息：可用工具列表、数据源、版本等。
    展示 MCP 的动态发现能力——客户端不需要提前知道有哪些工具。
    """
    return json.dumps({
        "server_name": "financial-tools-embedded",
        "transport": "stdio",
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
        "note": "这些工具是在运行时自动发现的，不需要在客户端硬编码导入。",
    }, ensure_ascii=False, indent=2)


# ============================================================
# 启动入口（stdio 模式，由子进程启动）
# ============================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")

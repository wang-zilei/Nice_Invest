"""
demo_comparison.py — Function Call vs MCP 对比演示脚本

运行：python -m src.mcp_integration.demo_comparison

这个脚本展示三种模式的核心差异：
1. Function Call：工具列表是硬编码的（import + @tool + bind_tools）
2. MCP 嵌入式：工具在运行时通过 stdio 自动发现（list_tools）
3. MCP SSE：工具在运行时通过 HTTP SSE 自动发现
4. MCP Resource：读取静态数据（Function Call 没有对应能力）

目的：通过实际运行结果，直观理解 Function Call 和 MCP 的区别。
"""
import sys
import os
import json
import io

# Windows 下 GBK 编码问题修复
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def demo_function_call():
    """演示 Function Call 模式：工具是硬编码的"""
    print_section("1. Function Call 模式（当前项目使用的方式）")

    print("\n【工具来源】硬编码导入（代码写死）")
    print("  代码示例：")
    print("    from src.mcp_tools.tushare_api import get_stock_basic")
    print("    from src.mcp_tools.calculator import calc_financial_ratio")
    print("    FUNDAMENTAL_TOOLS = [tool1, tool2, tool3, ...]")
    print("    llm.bind_tools(FUNDAMENTAL_TOOLS)")

    # 展示实际的硬编码工具列表
    print("\n【实际工具列表】（在代码中写死的）")
    try:
        from src.agents.analyst import FUNDAMENTAL_TOOLS
        print(f"  基本面 Agent 工具数: {len(FUNDAMENTAL_TOOLS)}")
        for t in FUNDAMENTAL_TOOLS:
            print(f"    - {t.name}: {t.description[:50]}...")
    except Exception as e:
        print(f"  加载失败: {e}")

    print("\n【特点】")
    print("  ✅ 简单直接，代码即文档")
    print("  ✅ 执行速度快（直接 Python 调用）")
    print("  ❌ 新增工具需要修改代码并重启 Agent")
    print("  ❌ 工具列表在编写时就固定了")
    print("  ❌ 无法跨语言（只能调用 Python 函数）")
    print("  ❌ 无法暴露静态数据（只能调用函数）")


def demo_mcp_embedded():
    """演示 MCP 嵌入式模式：工具运行时动态发现"""
    print_section("2. MCP 嵌入式模式（同进程，stdio 传输）")

    print("\n【工具来源】MCP Server（运行时自动发现）")
    print("  代码示例：")
    print("    client = MCPClient(mode='embedded')")
    print("    tools = client.list_tools()  # 动态发现！")
    print("    llm.bind_tools(tools)")

    print("\n【启动 MCP Server（stdio 子进程）...】")
    try:
        from src.mcp_integration.mcp_loader import load_mcp_tools, get_mcp_client

        mcp_tools = load_mcp_tools(mode="embedded")
        client = get_mcp_client(mode="embedded")

        print(f"\n【发现工具数】{len(mcp_tools)} 个")
        print("  工具列表（通过 MCP list_tools() 发现）：")
        for t in mcp_tools:
            print(f"    - {t.name}: {t.description[:60]}...")

        # 演示调用一个 MCP 工具
        print("\n【MCP 工具调用示例】")
        print("  调用 calc_financial_ratio_mcp(current_assets=100, current_liabilities=50)")
        try:
            ratio_tool = next((t for t in mcp_tools if t.name == "calc_financial_ratio_mcp"), None)
            if ratio_tool:
                result = ratio_tool.invoke({"current_assets": 100, "current_liabilities": 50})
                print(f"  结果: {result[:200]}")
            else:
                print("  未找到该工具")
        except Exception as e:
            print(f"  调用失败: {e}")

        # 演示 MCP Resource
        print("\n【MCP Resource 示例】（Function Call 没有的能力）")
        print("  读取 stock://registry/a_shares...")
        try:
            registry = client.read_resource("stock://registry/a_shares")
            data = json.loads(registry)
            if isinstance(data, list):
                print(f"  共 {len(data)} 只股票，前 3 只：")
                for item in data[:3]:
                    print(f"    {item}")
            elif isinstance(data, dict):
                print(f"  数据结构（前 3 个 key）：")
                for k, v in list(data.items())[:3]:
                    print(f"    {k}: {str(v)[:80]}")
        except Exception as e:
            print(f"  读取失败: {e}")

        print("\n【特点】")
        print("  ✅ 工具运行时自动发现，不需要硬编码")
        print("  ✅ 新增工具只需修改 MCP Server，Agent 代码不变")
        print("  ✅ 支持 Resource（静态数据暴露）")
        print("  ✅ 可以跨语言（Server 可用 TypeScript/Go/Rust 编写）")
        print("  ⚠️  有额外的协议开销（stdio 通信）")
        print("  ⚠️  需要维护 MCP Server 进程")

    except Exception as e:
        print(f"\n  ❌ 加载失败: {e}")
        import traceback
        traceback.print_exc()


def demo_mcp_sse():
    """演示 MCP SSE 模式：独立进程"""
    print_section("3. MCP 独立进程模式（SSE 传输）")

    print("\n【工具来源】独立 MCP Server 进程（HTTP SSE 连接）")
    print("  启动方式：")
    print("    终端1: python mcp_server_sse.py")
    print("    终端2: 运行本脚本（MCP_MODE=sse）")

    print("\n【请先在另一个终端运行: python mcp_server_sse.py】")
    print("  本脚本将尝试连接 http://127.0.0.1:8765/sse")

    try:
        from src.mcp_integration.mcp_loader import load_mcp_tools, get_mcp_client

        mcp_tools = load_mcp_tools(mode="sse")
        client = get_mcp_client(mode="sse")

        print(f"\n【发现工具数】{len(mcp_tools)} 个")
        print("  工具列表：")
        for t in mcp_tools:
            print(f"    - {t.name}: {t.description[:60]}...")

        print("\n【特点】")
        print("  ✅ Server 和 Agent 可部署在不同机器上")
        print("  ✅ 多个 Agent 可同时连接同一个 MCP Server")
        print("  ✅ 真正的微服务架构，可独立扩展")
        print("  ⚠️  需要额外启动 MCP Server 进程")
        print("  ⚠️  网络延迟比 stdio 略高")

    except ConnectionRefusedError:
        print("\n  ❌ 连接被拒绝：MCP Server 未启动")
        print("     请先运行: python mcp_server_sse.py")
    except Exception as e:
        print(f"\n  ❌ 连接失败: {e}")


def demo_summary():
    print_section("4. Function Call vs MCP 核心差异总结")

    print("""
┌─────────────────┬──────────────────────┬──────────────────────────┐
│      维度       │   Function Call      │   MCP                    │
├─────────────────┼──────────────────────┼──────────────────────────┤
│ 工具发现        │ 硬编码（编写时固定） │ 运行时自动发现           │
│ 工具执行        │ 直接 Python 调用     │ 通过协议转发（stdio/SSE）│
│ 新增工具        │ 修改代码 + 重启      │ 只改 Server，Agent 不变  │
│ 跨语言          │ 不支持               │ 支持（Server 任意语言）  │
│ 静态数据暴露    │ 不支持               │ 支持（Resource）         │
│ 部署            │ 单一进程             │ 可独立部署               │
│ 执行速度        │ 快（直接调用）       │ 略慢（协议开销）         │
│ 复杂度          │ 低                   │ 中                       │
│ 适用场景        │ 简单项目、快速原型   │ 多 Agent、跨语言、可扩展 │
└─────────────────┴──────────────────────┴──────────────────────────┘

一句话总结：
  Function Call = "我知道有哪些工具，直接调用"
  MCP = "先问 Server 有什么工具，然后通过协议调用"

MCP 的优势在以下场景体现：
  1. 多个 Agent/应用共享同一组工具（不需要各自 import）
  2. 工具用其他语言实现（TypeScript/Go/Rust）
  3. 工具需要独立部署、扩展、版本管理
  4. 需要暴露静态数据（Resource）给 Agent 读取

本项目（单进程、Python-only）使用 Function Call 完全够用。
MCP 更适合「工具即服务」的场景。
""")


if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("  Function Call vs MCP 对比演示")
    print("  通过实际运行理解两种模式的核心差异")
    print("█" * 60)

    demo_function_call()
    demo_mcp_embedded()
    demo_mcp_sse()
    demo_summary()

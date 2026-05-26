"""
mcp_loader.py — MCP 工具加载器（将 MCP Server 的工具转为 LangChain BaseTool）

这个模块是 MCP 和 LangChain 之间的桥梁。它：
1. 连接到 MCP Server（stdio 或 SSE 传输）
2. 调用 list_tools() 获取可用工具列表（动态发现）
3. 将每个 MCP 工具包装成 LangChain StructuredTool 对象
4. 调用时通过 MCP 协议转发给 Server 执行

对比 Function Call：Function Call 直接 import 函数 + @tool 装饰，
而 MCP 是通过协议连接 Server → list_tools() 发现工具 → call_tool() 执行。
"""
import asyncio
import json
import threading
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool


# ============================================================
# 异步事件循环管理
# ============================================================

_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_loop_lock = threading.Lock()


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """获取或创建一个后台事件循环（避免嵌套 asyncio.run 问题）"""
    global _loop, _loop_thread

    with _loop_lock:
        if _loop is not None and _loop.is_running():
            return _loop

        _loop = asyncio.new_event_loop()

        def run_loop():
            asyncio.set_event_loop(_loop)
            _loop.run_forever()

        _loop_thread = threading.Thread(target=run_loop, daemon=True)
        _loop_thread.start()
        return _loop


def _run_async(coro):
    """在后台事件循环中运行异步协程"""
    loop = _get_event_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=30)


# ============================================================
# MCP 客户端封装
# ============================================================

class MCPClient:
    """MCP 客户端，支持 stdio 和 SSE 两种传输模式。"""

    def __init__(self, mode: str = "embedded"):
        self.mode = mode
        self._session = None
        self._cleanup_func = None

    def connect(self):
        """连接到 MCP Server，获取会话。"""
        if self.mode == "embedded":
            self._session, self._cleanup_func = _run_async(
                self._connect_stdio()
            )
        elif self.mode == "sse":
            self._session, self._cleanup_func = _run_async(
                self._connect_sse()
            )
        else:
            raise ValueError(f"未知 MCP 模式: {self.mode}")
        return self

    async def _connect_stdio(self):
        """通过 stdio 连接嵌入式 MCP Server。"""
        from mcp.client.stdio import StdioServerParameters, stdio_client
        from mcp.client.session import ClientSession

        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server_embedded.py"],
        )
        stdio_transport = stdio_client(server_params)
        read, write = await stdio_transport.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        return session, lambda: asyncio.create_task(self._cleanup_stdio(stdio_transport, session))

    async def _connect_sse(self):
        """通过 SSE 连接独立进程 MCP Server。"""
        from mcp.client.sse import sse_client
        from mcp.client.session import ClientSession

        transport = sse_client(url="http://127.0.0.1:8765/sse")
        read, write = await transport.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        return session, lambda: asyncio.create_task(self._cleanup_sse(transport, session))

    async def _cleanup_stdio(self, transport, session):
        await session.__aexit__(None, None, None)
        await transport.__aexit__(None, None, None)

    async def _cleanup_sse(self, transport, session):
        await session.__aexit__(None, None, None)
        await transport.__aexit__(None, None, None)

    def list_tools(self) -> List[Dict[str, Any]]:
        """获取 MCP Server 暴露的所有工具列表。"""
        if self._session is None:
            self.connect()
        return _run_async(self._list_tools())

    async def _list_tools(self):
        result = await self._session.list_tools()
        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            })
        return tools

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """调用 MCP Server 上的工具。"""
        if self._session is None:
            self.connect()
        return _run_async(self._call_tool(tool_name, args))

    async def _call_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        result = await self._session.call_tool(tool_name, arguments=args)
        # MCP 返回的是 Content 列表，拼接为字符串
        parts = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
            else:
                parts.append(str(content))
        return "\n".join(parts)

    def read_resource(self, uri: str) -> str:
        """读取 MCP Server 暴露的资源。"""
        if self._session is None:
            self.connect()
        return _run_async(self._read_resource(uri))

    async def _read_resource(self, uri: str) -> str:
        result = await self._session.read_resource(uri=uri)
        parts = []
        for content in result.contents:
            if hasattr(content, "text"):
                parts.append(content.text)
            elif hasattr(content, "blob"):
                import base64
                parts.append(base64.b64decode(content.blob).decode("utf-8", errors="replace"))
        return "\n".join(parts)

    def cleanup(self):
        """清理连接。"""
        if self._cleanup_func:
            _run_async(self._cleanup_func())


# ============================================================
# 将 MCP 工具转为 LangChain StructuredTool
# ============================================================

# 缓存，避免重复连接
_client_cache: Dict[str, MCPClient] = {}
_langchain_tools_cache: Dict[str, List[StructuredTool]] = {}


def _build_langchain_tool(client: MCPClient, tool_info: Dict[str, Any]) -> StructuredTool:
    """
    将 MCP 工具信息包装成 LangChain StructuredTool。

    MCP 的 tool_info 格式:
    {
        "name": "get_stock_info_mcp",
        "description": "...",
        "input_schema": {
            "type": "object",
            "properties": {"ts_code": {"type": "string"}},
            "required": ["ts_code"]
        }
    }

    对比 Function Call：Function Call 的 schema 由 @tool 装饰器自动从函数签名推导，
    而 MCP 的 schema 由 Server 在 list_tools() 时返回。
    """
    name = tool_info["name"]
    description = tool_info["description"]
    input_schema = tool_info["input_schema"]

    def _call_mcp(**kwargs) -> str:
        """实际调用通过 MCP 协议转发到 Server 执行。"""
        return client.call_tool(name, kwargs)

    return StructuredTool(
        name=name,
        description=description,
        args_schema=None,  # MCP 已有 input_schema，此处不重复定义
        func=_call_mcp,
    )


def load_mcp_tools(mode: str = "embedded") -> List[StructuredTool]:
    """
    加载 MCP 工具为 LangChain StructuredTool 列表。

    流程：
    1. 连接 MCP Server
    2. 调用 list_tools() 获取工具列表（动态发现！）
    3. 将每个工具包装为 LangChain StructuredTool
    4. 返回 LangChain 可直接使用的工具列表（可传给 llm.bind_tools）

    对比 Function Call：
    - Function Call: from src.mcp_tools.xxx import foo; FUNDAMENTAL_TOOLS = [foo, bar, ...]
    - MCP: 连接 Server → list_tools() → 自动发现 → 包装 → 返回
    """
    if mode in _langchain_tools_cache:
        return _langchain_tools_cache[mode]

    client = MCPClient(mode=mode)
    client.connect()
    _client_cache[mode] = client

    tool_infos = client.list_tools()
    tools = [_build_langchain_tool(client, info) for info in tool_infos]

    _langchain_tools_cache[mode] = tools
    return tools


def get_mcp_client(mode: str = "embedded") -> MCPClient:
    """获取已连接的 MCP 客户端实例。"""
    if mode not in _client_cache:
        load_mcp_tools(mode)
    return _client_cache[mode]

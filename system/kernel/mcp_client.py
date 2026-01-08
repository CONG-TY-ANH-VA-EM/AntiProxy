"""
🔌 MCP (Model Context Protocol) Connectivity Layer.

Designation: Sys/Kernel/MCP
Purpose: Manages extrinsic cognitive extensions via the Model Context Protocol.
Capabilities:
- Multi-server connection multiplexing (Stdio/HTTP/SSE).
- Dynamic tool synthesis and registration.
- Fault-tolerant connection handling.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Third-party imports
from pydantic import BaseModel, Field, ConfigDict

# Internal System Imports
try:
    from system.config import settings, MCPServerConfig
except ImportError:
    # Fallback for legacy structure or direct execution
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from system.config import settings, MCPServerConfig

# ------------------------------------------------------------------------------
# Data Models (Schema First)
# ------------------------------------------------------------------------------

class MCPTool(BaseModel):
    """Represents a tool discovered from an extrinsic MCP node."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    original_name: str

    def get_prefixed_name(self, prefix: str = "") -> str:
        """Generates the namespaced identifier for the Agent's tool registry."""
        clean_prefix = prefix or ""
        return f"{clean_prefix}{self.server_name}_{self.original_name}"


class MCPServerConnection(BaseModel):
    """Maintains state for a specific MCP server link."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: MCPServerConfig
    session: Any = None  # mcp.ClientSession
    read_stream: Any = None
    write_stream: Any = None
    tools: List[MCPTool] = Field(default_factory=list)
    connected: bool = False
    error: Optional[str] = None
    _client_cm: Any = None  # Internal Context Manager

# ------------------------------------------------------------------------------
# Async Manager
# ------------------------------------------------------------------------------

class MCPClientManager:
    """
    Async Orchestrator for MCP Connections.
    
    Acts as the 'Neural Bridge' between the Agent Kernel and external
    capabilities (GitHub, Filesystem, Database) provided via MCP.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or settings.MCP_SERVERS_CONFIG
        self.servers: Dict[str, MCPServerConnection] = {}
        self.tool_prefix = settings.MCP_TOOL_PREFIX
        self._initialized = False
        self._lock = asyncio.Lock()

    def _load_server_configs(self) -> List[MCPServerConfig]:
        """Parses the MCP configuration manifest."""
        config_file = Path(self.config_path)

        if not config_file.exists():
            print(f"   [MCP] ⚠️ Config manifest missing: {config_file}")
            return []

        try:
            content = config_file.read_text(encoding="utf-8")
            data = json.loads(content)
            
            configs = []
            for server_data in data.get("servers", []):
                if server_data.get("enabled", True):
                    configs.append(MCPServerConfig(**server_data))
            return configs

        except Exception as e:
            print(f"   [MCP] ❌ Manifest Parse Error: {e}")
            return []

    async def initialize(self) -> None:
        """Bootstraps all defined MCP connections."""
        async with self._lock:
            if self._initialized: return

            if not settings.MCP_ENABLED:
                print("   [MCP] Integration Disabled via Settings.")
                return

            print("   [MCP] 🔌 Initializing Neural Bridges...")
            configs = self._load_server_configs()

            if not configs:
                print("   [MCP] No active server configurations found.")
                return

            # Parallel connection attempts could be implemented here
            for config in configs:
                await self._connect_server(config)

            # Telemetry
            connected = sum(1 for s in self.servers.values() if s.connected)
            tools = sum(len(s.tools) for s in self.servers.values())
            print(f"   [MCP] ✅ Status: {connected}/{len(configs)} Online | {tools} Tools Mounted")
            
            self._initialized = True

    async def _connect_server(self, config: MCPServerConfig) -> None:
        """Establishes the transport layer to a single node."""
        connection = MCPServerConnection(config=config)
        self.servers[config.name] = connection

        try:
            print(f"      🔗 Linking: {config.name} ({config.transport})...")

            if config.transport == "stdio":
                await self._connect_stdio(connection)
            elif config.transport in ("http", "streamable-http"):
                await self._connect_http(connection)
            elif config.transport == "sse":
                await self._connect_sse(connection)
            else:
                raise ValueError(f"Unknown transport protocol: {config.transport}")

            if connection.connected and connection.session:
                await self._discover_tools(connection)
                print(f"         ✓ Mounted {len(connection.tools)} capabilities.")

        except ImportError:
            connection.error = "Library 'mcp' missing"
            print(f"      ❌ Missing Dependency: pip install 'mcp[cli]'")
        except Exception as e:
            connection.error = str(e)
            print(f"      ❌ Connection Failure: {e}")

    async def _connect_stdio(self, connection: MCPServerConnection) -> None:
        """Protocol: STDIO Pipe."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        if not connection.config.command:
            raise ValueError("STDIO transport requires 'command'")

        server_params = StdioServerParameters(
            command=connection.config.command,
            args=connection.config.args,
            env={**os.environ, **connection.config.env},
        )

        client_cm = stdio_client(server_params)
        read_stream, write_stream = await client_cm.__aenter__()
        
        connection.read_stream = read_stream
        connection.write_stream = write_stream
        connection._client_cm = client_cm

        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()

        connection.session = session
        connection.connected = True

    async def _connect_http(self, connection: MCPServerConnection) -> None:
        """Protocol: Streamable HTTP."""
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        if not connection.config.url:
            raise ValueError("HTTP transport requires 'url'")

        client_cm = streamablehttp_client(connection.config.url)
        read_stream, write_stream, _ = await client_cm.__aenter__()

        connection.read_stream = read_stream
        connection.write_stream = write_stream
        connection._client_cm = client_cm

        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()

        connection.session = session
        connection.connected = True

    async def _connect_sse(self, connection: MCPServerConnection) -> None:
        """Protocol: Server-Sent Events (Alias for HTTP in current SDK)."""
        await self._connect_http(connection)

    async def _discover_tools(self, connection: MCPServerConnection) -> None:
        """Queries the node for its capabilities manifest."""
        if not connection.session: return

        try:
            tools_response = await connection.session.list_tools()
            
            for tool in tools_response.tools:
                mcp_tool = MCPTool(
                    name=tool.name,
                    description=tool.description or "No description.",
                    server_name=connection.config.name,
                    input_schema=tool.inputSchema or {},
                    original_name=tool.name,
                )
                connection.tools.append(mcp_tool)
        except Exception as e:
            print(f"      ⚠️ Discovery Error [{connection.config.name}]: {e}")

    def get_all_tools_as_callables(self) -> Dict[str, Callable[..., Any]]:
        """Synthesizes Python callables from MCP definitions."""
        callables: Dict[str, Callable[..., Any]] = {}
        for connection in self.servers.values():
            if not connection.connected: continue

            for tool in connection.tools:
                prefixed_name = tool.get_prefixed_name(self.tool_prefix)
                callables[prefixed_name] = self._create_tool_wrapper(connection, tool)
        return callables

    def _create_tool_wrapper(self, connection: MCPServerConnection, tool: MCPTool) -> Callable[..., Any]:
        """Creates a closure that acts as the local proxy for the remote tool."""
        
        async def tool_proxy(**kwargs: Any) -> Any:
            if not connection.connected or not connection.session:
                return "Error: Connection lost."
            
            try:
                result = await connection.session.call_tool(tool.original_name, arguments=kwargs)
                
                # Unpack standard MCP content types
                if hasattr(result, "content") and result.content:
                    contents = []
                    for content in result.content:
                        if hasattr(content, "text"): contents.append(content.text)
                        elif hasattr(content, "data"): contents.append(f"<Binary Data: {len(content.data)} bytes>")
                    return "\n".join(contents) if contents else str(result)
                
                return str(result)
            except Exception as e:
                return f"MCP Execution Error: {e}"

        # Prompt Engineering Metadata
        tool_proxy.__name__ = tool.get_prefixed_name(self.tool_prefix)
        tool_proxy.__doc__ = (
            f"EXTERNAL TOOL [MCP:{connection.config.name}]\n"
            f"{tool.description}\n"
            f"Input Schema: {json.dumps(tool.input_schema)}"
        )
        
        return tool_proxy

    async def shutdown(self) -> None:
        """Terminates all connections."""
        for name, connection in self.servers.items():
            try:
                if connection.session:
                    await connection.session.__aexit__(None, None, None)
                if connection._client_cm:
                    await connection._client_cm.__aexit__(None, None, None)
            except Exception:
                pass
        self.servers.clear()
        self._initialized = False

# ------------------------------------------------------------------------------
# Synchronous Bridge
# ------------------------------------------------------------------------------

class MCPClientManagerSync:
    """
    Synchronous Interface for the MCP Manager.
    Required because the Agent Kernel operates on a blocking event loop.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._async_manager = MCPClientManager(config_path)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Safely retrieves or creates an event loop."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop

    def initialize(self) -> None:
        """Sync wrapper for init."""
        try:
            loop = self._get_loop()
            if loop.is_running():
                # If we are already in an async context, we shouldn't be here ideally,
                # but if we are, we use create_task (not implemented here for simplicity)
                print("   [MCP] ⚠️ Warning: Running sync init in active loop.")
            else:
                loop.run_until_complete(self._async_manager.initialize())
        except Exception as e:
            print(f"   [MCP] Init Failed: {e}")

    def get_all_tools_as_callables(self) -> Dict[str, Callable[..., Any]]:
        """Wraps async tools in sync executors."""
        async_map = self._async_manager.get_all_tools_as_callables()
        sync_map: Dict[str, Callable[..., Any]] = {}

        for name, afn in async_map.items():
            def sync_proxy(**kwargs: Any) -> Any:
                loop = self._get_loop()
                if loop.is_running():
                    # Handle nested loop case roughly
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        return pool.submit(asyncio.run, afn(**kwargs)).result()
                return loop.run_until_complete(afn(**kwargs))
            
            sync_proxy.__name__ = afn.__name__
            sync_proxy.__doc__ = afn.__doc__
            sync_map[name] = sync_proxy
            
        return sync_map

    def shutdown(self) -> None:
        loop = self._get_loop()
        if not loop.is_running():
            loop.run_until_complete(self._async_manager.shutdown())

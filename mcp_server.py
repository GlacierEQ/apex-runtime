#!/usr/bin/env python3
"""
MCP Server — Deploy the Connector Runtime as an MCP Server
Exposes connectors as MCP tools.

Usage:
    python3 mcp_server.py --port 8000
    python3 mcp_server.py --port 8000 --connectors github,filesystem
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from connector_runtime import (
    ConnectorRuntime, BaseConnector, GitHubConnector, FilesystemConnector,
)


class MCPServer:
    """MCP Server wrapping connectors."""

    def __init__(self, runtime: ConnectorRuntime, port: int = 8000) -> None:
        self.runtime = runtime
        self.port = port
        self._running = False

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "initialize":
            return self._handle_initialize(params)
        elif method == "tools/list":
            return self._handle_list_tools(params)
        elif method == "tools/call":
            return await self._handle_call_tool(params)
        elif method == "health":
            return self._handle_health(params)
        else:
            return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": "apex-mcp-server",
                "version": "1.0.0",
            },
        }

    def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = self.runtime.list_tools()
        return {
            "tools": [
                {
                    "name": f"{t['connector']}_{t['name']}",
                    "description": f"[{t['connector']}] {t['description']}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                    },
                }
                for t in tools
            ]
        }

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        # Parse connector/tool name
        parts = tool_name.split("_", 1)
        if len(parts) != 2:
            return {"error": {"code": -32602, "message": f"Invalid tool name: {tool_name}"}}

        connector_name, tool_name = parts

        try:
            result = await self.runtime.call_tool(connector_name, tool_name, arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ]
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def _handle_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check."""
        return self.runtime.health_check()

    async def run(self) -> None:
        """Run the MCP server."""
        self._running = True
        print(f"MCP Server running on port {self.port}")
        print(f"Connectors: {', '.join(self.runtime.connectors.keys())}")
        print(f"Tools: {len(self.runtime.list_tools())}")
        print("\nReady for connections.")

        # Simple stdio server for testing
        while self._running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break

                request = json.loads(line.strip())
                response = await self.handle_request(request)
                print(json.dumps(response))
            except EOFError:
                break
            except Exception as e:
                print(json.dumps({"error": {"code": -32603, "message": str(e)}}))

    def stop(self) -> None:
        """Stop the server."""
        self._running = False


def create_server(port: int = 8000, connector_names: Optional[List[str]] = None) -> MCPServer:
    """Create an MCP server with specified connectors."""
    runtime = ConnectorRuntime()

    # Register connectors
    all_connectors = {
        "github": GitHubConnector,
        "filesystem": FilesystemConnector,
    }

    if connector_names:
        for name in connector_names:
            if name in all_connectors:
                runtime.register(name, all_connectors[name]())
    else:
        for name, cls in all_connectors.items():
            runtime.register(name, cls())

    return MCPServer(runtime, port)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="APEX MCP Server")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--connectors", help="Comma-separated connector names")
    parser.add_argument("--list", action="store_true", help="List available connectors")

    args = parser.parse_args()

    if args.list:
        print("Available connectors:")
        print("  github - GitHub API connector")
        print("  filesystem - Filesystem operations")
        return 0

    connector_names = args.connectors.split(",") if args.connectors else None
    server = create_server(args.port, connector_names)

    asyncio.run(server.run())
    return 0


if __name__ == "__main__":
    sys.exit(main())

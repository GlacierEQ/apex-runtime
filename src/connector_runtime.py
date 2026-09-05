#!/usr/bin/env python3
"""
Connector Runtime — MCP Server That Runs Connectors
Wraps tools and services as MCP servers.

Usage:
    from connector_runtime import ConnectorRuntime

    runtime = ConnectorRuntime()
    runtime.register("github", GitHubConnector())
    runtime.start(port=8000)
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class ConnectorStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ConnectorInfo:
    """Information about a connector."""
    name: str
    description: str
    version: str
    status: ConnectorStatus = ConnectorStatus.UNKNOWN
    tools: List[Dict[str, str]] = field(default_factory=list)
    last_health_check: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "tools": self.tools,
            "last_health_check": self.last_health_check,
        }


class BaseConnector:
    """Base class for connectors."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._tools: List[Dict[str, str]] = []

    def register_tool(self, name: str, description: str, handler: Callable) -> None:
        """Register a tool."""
        self._tools.append({
            "name": name,
            "description": description,
        })
        setattr(self, f"tool_{name}", handler)

    def get_info(self) -> ConnectorInfo:
        """Get connector info."""
        return ConnectorInfo(
            name=self.name,
            description=self.description,
            version="1.0.0",
            status=ConnectorStatus.HEALTHY,
            tools=self._tools,
            last_health_check=time.time(),
        )

    def health_check(self) -> ConnectorStatus:
        """Check connector health."""
        return ConnectorStatus.HEALTHY

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool."""
        handler = getattr(self, f"tool_{name}", None)
        if handler:
            return await handler(arguments) if callable(handler) else handler
        raise ValueError(f"Unknown tool: {name}")


class GitHubConnector(BaseConnector):
    """GitHub connector."""

    def __init__(self) -> None:
        super().__init__("github", "GitHub API connector")
        self.register_tool("list_repos", "List repositories", self._list_repos)
        self.register_tool("get_repo", "Get repository info", self._get_repo)

    async def _list_repos(self, args: Dict[str, Any]) -> Any:
        """List repositories."""
        return {"repos": []}

    async def _get_repo(self, args: Dict[str, Any]) -> Any:
        """Get repository."""
        return {"repo": {}}


class FilesystemConnector(BaseConnector):
    """Filesystem connector."""

    def __init__(self) -> None:
        super().__init__("filesystem", "Filesystem operations")
        self.register_tool("read", "Read file", self._read)
        self.register_tool("write", "Write file", self._write)
        self.register_tool("list", "List directory", self._list)

    async def _read(self, args: Dict[str, Any]) -> Any:
        """Read file."""
        path = args.get("path", "")
        try:
            content = Path(path).read_text()
            return {"content": content}
        except Exception as e:
            return {"error": str(e)}

    async def _write(self, args: Dict[str, Any]) -> Any:
        """Write file."""
        path = args.get("path", "")
        content = args.get("content", "")
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    async def _list(self, args: Dict[str, Any]) -> Any:
        """List directory."""
        path = args.get("path", ".")
        try:
            entries = list(Path(path).iterdir())
            return {"entries": [str(e.name) for e in entries]}
        except Exception as e:
            return {"error": str(e)}


class ConnectorRuntime:
    """MCP server that runs connectors."""

    def __init__(self) -> None:
        self.connectors: Dict[str, BaseConnector] = {}
        self._start_time = time.time()

    def register(self, name: str, connector: BaseConnector) -> None:
        """Register a connector."""
        self.connectors[name] = connector

    def unregister(self, name: str) -> bool:
        """Unregister a connector."""
        if name in self.connectors:
            del self.connectors[name]
            return True
        return False

    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """Get a connector."""
        return self.connectors.get(name)

    def list_connectors(self) -> List[ConnectorInfo]:
        """List all connectors."""
        return [c.get_info() for c in self.connectors.values()]

    def list_tools(self) -> List[Dict[str, str]]:
        """List all tools across connectors."""
        tools = []
        for connector in self.connectors.values():
            info = connector.get_info()
            for tool in info.tools:
                tools.append({
                    "connector": connector.name,
                    "name": tool["name"],
                    "description": tool["description"],
                })
        return tools

    async def call_tool(self, connector_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on a connector."""
        connector = self.connectors.get(connector_name)
        if not connector:
            raise ValueError(f"Unknown connector: {connector_name}")
        return await connector.call_tool(tool_name, arguments)

    def health_check(self) -> Dict[str, Any]:
        """Check health of all connectors."""
        results = {}
        for name, connector in self.connectors.items():
            status = connector.health_check()
            results[name] = {
                "status": status.value,
                "healthy": status == ConnectorStatus.HEALTHY,
            }
        return {
            "status": "healthy" if all(r["healthy"] for r in results.values()) else "degraded",
            "uptime": time.time() - self._start_time,
            "connectors": results,
        }

    def get_info(self) -> Dict[str, Any]:
        """Get runtime info."""
        return {
            "connectors": len(self.connectors),
            "tools": len(self.list_tools()),
            "uptime": time.time() - self._start_time,
        }

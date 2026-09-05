#!/usr/bin/env python3
"""
State Persistence — Session Memory Across Runs
Stores and retrieves state between sessions.

Usage:
    from state_store import StateStore

    store = StateStore("~/.apex/state")
    store.set("last_task", "build MCP server")
    store.get("last_task")  # "build MCP server"
    store.history()  # List all stored state
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StateEntry:
    """A single state entry."""
    key: str
    value: Any
    timestamp: float
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


class StateStore:
    """Persistent state storage across sessions."""

    def __init__(self, base_dir: str = "~/.apex/state") -> None:
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.base_dir / "state.json"
        self.history_file = self.base_dir / "history.jsonl"
        self._load()

    def _load(self) -> None:
        """Load state from disk."""
        if self.state_file.exists():
            self.state = json.loads(self.state_file.read_text())
        else:
            self.state = {}

    def _save(self) -> None:
        """Save state to disk."""
        self.state_file.write_text(json.dumps(self.state, indent=2, default=str))

    def set(self, key: str, value: Any, session_id: str = "", **metadata) -> None:
        """Set a state value."""
        entry = StateEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            session_id=session_id,
            metadata=metadata,
        )
        self.state[key] = entry.to_dict()
        self._save()
        self._append_history(entry)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        entry = self.state.get(key)
        if entry:
            return entry.get("value", default)
        return default

    def get_entry(self, key: str) -> Optional[StateEntry]:
        """Get full state entry."""
        data = self.state.get(key)
        if data:
            return StateEntry(**data)
        return None

    def delete(self, key: str) -> bool:
        """Delete a state entry."""
        if key in self.state:
            del self.state[key]
            self._save()
            return True
        return False

    def keys(self) -> List[str]:
        """Get all keys."""
        return list(self.state.keys())

    def items(self) -> Dict[str, Any]:
        """Get all items."""
        return {k: v.get("value") for k, v in self.state.items()}

    def clear(self) -> None:
        """Clear all state."""
        self.state = {}
        self._save()

    def history(self, limit: int = 50) -> List[StateEntry]:
        """Get state history."""
        if not self.history_file.exists():
            return []

        entries = []
        lines = self.history_file.read_text().strip().split("\n")
        for line in lines[-limit:]:
            if line:
                data = json.loads(line)
                entries.append(StateEntry(**data))
        return entries

    def _append_history(self, entry: StateEntry) -> None:
        """Append to history log."""
        with open(self.history_file, "a") as f:
            f.write(json.dumps(entry.to_dict(), default=str) + "\n")

    def search(self, query: str) -> List[StateEntry]:
        """Search state by key or value."""
        results = []
        query_lower = query.lower()
        for key, data in self.state.items():
            if query_lower in key.lower():
                results.append(StateEntry(**data))
            elif query_lower in str(data.get("value", "")).lower():
                results.append(StateEntry(**data))
        return results

    def export(self) -> Dict[str, Any]:
        """Export all state."""
        return {
            "state": self.state,
            "history": [e.to_dict() for e in self.history()],
            "exported_at": time.time(),
        }

    def import_state(self, data: Dict[str, Any]) -> None:
        """Import state from export."""
        if "state" in data:
            self.state.update(data["state"])
            self._save()

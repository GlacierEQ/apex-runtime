#!/usr/bin/env python3
"""
Search/Discovery — Index and Search Across Estate
Indexes repositories, files, and skills for fast search.

Usage:
    from search_engine import SearchEngine

    engine = SearchEngine("~/.apex/index")
    engine.index_repo("/path/to/repo")
    results = engine.search("MCP server")
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class SearchResult:
    """A search result."""
    path: str
    name: str
    type: str  # file, function, class, skill
    score: float
    context: str = ""
    line: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "type": self.type,
            "score": self.score,
            "context": self.context,
            "line": self.line,
        }


@dataclass
class IndexEntry:
    """An indexed entry."""
    path: str
    name: str
    type: str
    content_hash: str
    indexed_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "type": self.type,
            "content_hash": self.content_hash,
            "indexed_at": self.indexed_at,
            "metadata": self.metadata,
        }


class SearchEngine:
    """Search and discovery engine."""

    def __init__(self, index_dir: str = "~/.apex/index") -> None:
        self.index_dir = Path(index_dir).expanduser()
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        """Load index from disk."""
        if self.index_path.exists():
            data = json.loads(self.index_path.read_text())
            self.index = {k: IndexEntry(**v) for k, v in data.items()}
        else:
            self.index = {}

    def _save_index(self) -> None:
        """Save index to disk."""
        data = {k: v.to_dict() for k, v in self.index.items()}
        self.index_path.write_text(json.dumps(data, indent=2))

    def _content_hash(self, content: str) -> str:
        """Calculate content hash."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def index_single_file(self, filepath: Path) -> bool:
        """Index a single file."""
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            content_hash = self._content_hash(content)

            # Skip if unchanged
            entry = self.index.get(str(filepath))
            if entry and entry.content_hash == content_hash:
                return False

            # Determine type
            file_type = self._detect_type(filepath, content)

            # Extract symbols
            symbols = self._extract_symbols(content, file_type)

            self.index[str(filepath)] = IndexEntry(
                path=str(filepath),
                name=filepath.stem,
                type=file_type,
                content_hash=content_hash,
                indexed_at=time.time(),
                metadata={
                    "size": len(content),
                    "lines": content.count("\n"),
                    "symbols": symbols,
                },
            )
            return True
        except Exception:
            return False

    def index_directory(self, dirpath: Path, recursive: bool = True) -> int:
        """Index a directory."""
        count = 0
        pattern = "**/*.py" if recursive else "*.py"

        for filepath in dirpath.glob(pattern):
            # Skip hidden and cache dirs
            if any(part.startswith(".") or part == "__pycache__" for part in filepath.parts):
                continue
            if self.index_single_file(filepath):
                count += 1

        self._save_index()
        return count

    def index_repo(self, repo_path: str) -> Dict[str, Any]:
        """Index a repository."""
        path = Path(repo_path)
        start = time.time()

        files_indexed = self.index_directory(path)
        duration = time.time() - start

        return {
            "repo": str(path),
            "files_indexed": files_indexed,
            "total_indexed": len(self.index),
            "duration_ms": duration * 1000,
        }

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Search the index."""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for path, entry in self.index.items():
            score = 0.0

            # Name match
            if query_lower in entry.name.lower():
                score += 1.0

            # Symbol match
            symbols = entry.metadata.get("symbols", [])
            for symbol in symbols:
                if query_lower in symbol.lower():
                    score += 0.8
                for word in query_words:
                    if word in symbol.lower():
                        score += 0.3

            # Type bonus
            if "skill" in query_lower and entry.type == "skill":
                score += 0.5
            if "test" in query_lower and entry.type == "test":
                score += 0.5

            if score > 0:
                results.append(SearchResult(
                    path=path,
                    name=entry.name,
                    type=entry.type,
                    score=score,
                    context=f"Symbols: {', '.join(symbols[:5])}",
                ))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def search_by_type(self, file_type: str) -> List[IndexEntry]:
        """Search by file type."""
        return [e for e in self.index.values() if e.type == file_type]

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        types = {}
        for entry in self.index.values():
            types[entry.type] = types.get(entry.type, 0) + 1

        return {
            "total_files": len(self.index),
            "types": types,
            "last_indexed": max((e.indexed_at for e in self.index.values()), default=0),
        }

    def _detect_type(self, filepath: Path, content: str) -> str:
        """Detect file type."""
        name = filepath.name.lower()

        if "test" in name:
            return "test"
        if name.endswith("_forge.py") or "forge" in name:
            return "forge"
        if "skill" in name:
            return "skill"
        if "connector" in name:
            return "connector"
        if "config" in name or "settings" in name:
            return "config"
        if name.startswith("test_"):
            return "test"

        return "source"

    def _extract_symbols(self, content: str, file_type: str) -> List[str]:
        """Extract symbols from content."""
        symbols = []

        # Python symbols
        for match in re.finditer(r"^def (\w+)", content, re.MULTILINE):
            symbols.append(match.group(1))
        for match in re.finditer(r"^class (\w+)", content, re.MULTILINE):
            symbols.append(match.group(1))

        return symbols

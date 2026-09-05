#!/usr/bin/env python3
"""
Skill Registry — Index of All Available Skills
Indexes and discovers skills across the estate.

Usage:
    from skill_registry import SkillRegistry

    registry = SkillRegistry("~/.apex/skills")
    registry.register("/path/to/skill")
    results = registry.search("MCP")
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SkillInfo:
    """Information about a skill."""
    name: str
    description: str
    path: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    registered_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "category": self.category,
            "tags": self.tags,
            "triggers": self.triggers,
            "tools": self.tools,
            "version": self.version,
            "registered_at": self.registered_at,
        }


class SkillRegistry:
    """Skill discovery and registry."""

    def __init__(self, registry_dir: str = "~/.apex/skills") -> None:
        self.registry_dir = Path(registry_dir).expanduser()
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "registry.json"
        self.skills: Dict[str, SkillInfo] = {}
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_file.exists():
            data = json.loads(self.registry_file.read_text())
            self.skills = {k: SkillInfo(**v) for k, v in data.items()}

    def _save(self) -> None:
        """Save registry to disk."""
        data = {k: v.to_dict() for k, v in self.skills.items()}
        self.registry_file.write_text(json.dumps(data, indent=2))

    def register(self, skill_path: str) -> SkillInfo:
        """Register a skill from a file or directory."""
        path = Path(skill_path)

        if path.is_dir():
            return self._register_directory(path)
        else:
            return self._register_file(path)

    def _register_file(self, filepath: Path) -> SkillInfo:
        """Register a single skill file."""
        content = filepath.read_text(encoding="utf-8", errors="ignore")

        # Parse skill
        name = filepath.stem
        description = self._extract_description(content)
        category = self._detect_category(name, content)
        tags = self._extract_tags(content)
        triggers = self._extract_triggers(content)
        tools = self._extract_tools(content)

        skill = SkillInfo(
            name=name,
            description=description,
            path=str(filepath),
            category=category,
            tags=tags,
            triggers=triggers,
            tools=tools,
            registered_at=time.time(),
        )

        self.skills[name] = skill
        self._save()
        return skill

    def _register_directory(self, dirpath: Path) -> SkillInfo:
        """Register a skill directory."""
        # Look for SKILL.md or README.md
        for readme in ["SKILL.md", "README.md"]:
            readme_path = dirpath / readme
            if readme_path.exists():
                return self._register_file(readme_path)

        # Fall back to directory name
        return SkillInfo(
            name=dirpath.name,
            description="",
            path=str(dirpath),
            category="general",
            registered_at=time.time(),
        )

    def unregister(self, name: str) -> bool:
        """Unregister a skill."""
        if name in self.skills:
            del self.skills[name]
            self._save()
            return True
        return False

    def get(self, name: str) -> Optional[SkillInfo]:
        """Get a skill by name."""
        return self.skills.get(name)

    def list_all(self) -> List[SkillInfo]:
        """List all registered skills."""
        return list(self.skills.values())

    def list_by_category(self, category: str) -> List[SkillInfo]:
        """List skills by category."""
        return [s for s in self.skills.values() if s.category == category]

    def search(self, query: str) -> List[SkillInfo]:
        """Search skills by name, description, or tags."""
        results = []
        query_lower = query.lower()

        for skill in self.skills.values():
            score = 0.0

            if query_lower in skill.name.lower():
                score += 1.0
            if query_lower in skill.description.lower():
                score += 0.5
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 0.3
            for trigger in skill.triggers:
                if query_lower in trigger.lower():
                    score += 0.4

            if score > 0:
                results.append(skill)

        return results

    def get_categories(self) -> List[str]:
        """Get all categories."""
        return list(set(s.category for s in self.skills.values()))

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        categories = {}
        for skill in self.skills.values():
            categories[skill.category] = categories.get(skill.category, 0) + 1

        return {
            "total_skills": len(self.skills),
            "categories": categories,
            "last_registered": max((s.registered_at for s in self.skills.values()), default=0),
        }

    def _extract_description(self, content: str) -> str:
        """Extract description from skill content."""
        # Look for first paragraph after title
        lines = content.split("\n")
        in_body = False
        description_lines = []

        for line in lines:
            if line.startswith("# "):
                in_body = True
                continue
            if in_body:
                if line.startswith("## "):
                    break
                if line.strip():
                    description_lines.append(line.strip())

        return " ".join(description_lines)[:200]

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content."""
        tags = []

        # Look for tag patterns
        tag_patterns = [
            r"tags?:\s*(.+)",
            r"keywords?:\s*(.+)",
            r"#(\w+)",
        ]

        for pattern in tag_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                tags.extend([t.strip() for t in match.group(1).split(",")])

        return list(set(tags))

    def _extract_triggers(self, content: str) -> List[str]:
        """Extract trigger phrases from content."""
        triggers = []

        # Look for trigger patterns
        trigger_patterns = [
            r"trigger[s]?:\s*(.+)",
            r"activate[s]?:\s*(.+)",
            r"use\s+when:\s*(.+)",
        ]

        for pattern in trigger_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                triggers.extend([t.strip() for t in match.group(1).split(",")])

        return triggers

    def _extract_tools(self, content: str) -> List[str]:
        """Extract tools from content."""
        tools = []

        # Look for tool patterns
        tool_patterns = [
            r"tools?:\s*(.+)",
            r"commands?:\s*(.+)",
            r"functions?:\s*(.+)",
        ]

        for pattern in tool_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                tools.extend([t.strip() for t in match.group(1).split(",")])

        return tools

    def _detect_category(self, name: str, content: str) -> str:
        """Detect category from name and content."""
        combined = f"{name} {content}".lower()

        if "pipeline" in combined or "forge" in combined:
            return "pipelines"
        if "test" in combined:
            return "testing"
        if "deploy" in combined or "ci" in combined:
            return "deployment"
        if "security" in combined or "audit" in combined:
            return "security"
        if "mcp" in combined or "connector" in combined:
            return "connectors"
        if "skill" in combined or "learning" in combined:
            return "skills"
        if "doc" in combined or "readme" in combined:
            return "documentation"

        return "general"

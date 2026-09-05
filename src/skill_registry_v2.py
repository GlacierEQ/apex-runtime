#!/usr/bin/env python3
"""
Skill Registry — Versioned Skill Tracking
Inspired by mega-skills registry pattern.

Tracks skills with versions, dependencies, and metadata.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SkillEntry:
    """A registered skill entry."""
    id: str
    name: str
    version: str
    path: str
    entrypoint: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    registered_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "path": self.path,
            "entrypoint": self.entrypoint,
            "description": self.description,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "registered_at": self.registered_at,
            "updated_at": self.updated_at,
        }


class SkillRegistry:
    """Versioned skill registry."""

    def __init__(self, registry_dir: str = "~/.apex/registry") -> None:
        self.registry_dir = Path(registry_dir).expanduser()
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "skills.json"
        self.skills: Dict[str, SkillEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_file.exists():
            data = json.loads(self.registry_file.read_text())
            self.skills = {k: SkillEntry(**v) for k, v in data.items()}

    def _save(self) -> None:
        """Save registry to disk."""
        data = {k: v.to_dict() for k, v in self.skills.items()}
        self.registry_file.write_text(json.dumps(data, indent=2))

    def register(self, skill: SkillEntry) -> None:
        """Register a skill."""
        skill.registered_at = time.time()
        skill.updated_at = time.time()
        self.skills[skill.id] = skill
        self._save()

    def unregister(self, skill_id: str) -> bool:
        """Unregister a skill."""
        if skill_id in self.skills:
            del self.skills[skill_id]
            self._save()
            return True
        return False

    def get(self, skill_id: str) -> Optional[SkillEntry]:
        """Get a skill by ID."""
        return self.skills.get(skill_id)

    def update(self, skill_id: str, **kwargs) -> bool:
        """Update a skill."""
        skill = self.skills.get(skill_id)
        if not skill:
            return False

        for key, value in kwargs.items():
            if hasattr(skill, key):
                setattr(skill, key, value)

        skill.updated_at = time.time()
        self._save()
        return True

    def list_all(self) -> List[SkillEntry]:
        """List all registered skills."""
        return list(self.skills.values())

    def list_by_tag(self, tag: str) -> List[SkillEntry]:
        """List skills by tag."""
        return [s for s in self.skills.values() if tag in s.tags]

    def search(self, query: str) -> List[SkillEntry]:
        """Search skills by name or description."""
        results = []
        query_lower = query.lower()

        for skill in self.skills.values():
            if query_lower in skill.name.lower() or query_lower in skill.description.lower():
                results.append(skill)

        return results

    def validate_dependencies(self) -> List[str]:
        """Validate all skill dependencies exist."""
        missing = []
        for skill in self.skills.values():
            for dep in skill.dependencies:
                if dep not in self.skills:
                    missing.append(f"{skill.id} depends on missing {dep}")
        return missing

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        tags = {}
        for skill in self.skills.values():
            for tag in skill.tags:
                tags[tag] = tags.get(tag, 0) + 1

        return {
            "total_skills": len(self.skills),
            "tags": tags,
            "last_registered": max((s.registered_at for s in self.skills.values()), default=0),
        }

#!/usr/bin/env python3
"""
Documentation Site — Central Docs Hub
Aggregates READMEs into a central documentation site.

Usage:
    from doc_site import DocSite

    site = DocSite("~/.apex/docs")
    site.add_repo("/path/to/repo")
    site.generate()
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DocPage:
    """A documentation page."""
    title: str
    source: str
    content: str
    category: str = "general"
    last_updated: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "last_updated": self.last_updated,
            "metadata": self.metadata,
        }


@dataclass
class DocSection:
    """A documentation section."""
    title: str
    pages: List[DocPage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "pages": [p.to_dict() for p in self.pages],
        }


class DocSite:
    """Central documentation hub."""

    def __init__(self, docs_dir: str = "~/.apex/docs") -> None:
        self.docs_dir = Path(docs_dir).expanduser()
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.pages: List[DocPage] = []
        self.sections: Dict[str, DocSection] = {}

    def add_repo(self, repo_path: str) -> int:
        """Add documentation from a repository."""
        path = Path(repo_path)
        count = 0

        # Find README files
        for readme in path.glob("README*"):
            content = readme.read_text(encoding="utf-8", errors="ignore")
            title = self._extract_title(content) or path.name

            page = DocPage(
                title=title,
                source=str(readme),
                content=content,
                category=self._detect_category(path.name),
                last_updated=readme.stat().st_mtime,
                metadata={"repo": path.name},
            )
            self.pages.append(page)
            count += 1

        # Find other docs
        for doc in path.glob("docs/**/*.md"):
            content = doc.read_text(encoding="utf-8", errors="ignore")
            title = self._extract_title(content) or doc.stem

            page = DocPage(
                title=title,
                source=str(doc),
                content=content,
                category=self._detect_category(path.name),
                last_updated=doc.stat().st_mtime,
                metadata={"repo": path.name, "path": str(doc.relative_to(path))},
            )
            self.pages.append(page)
            count += 1

        return count

    def add_directory(self, dir_path: str) -> int:
        """Add documentation from a directory."""
        path = Path(dir_path)
        count = 0

        for md_file in path.glob("**/*.md"):
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            title = self._extract_title(content) or md_file.stem

            page = DocPage(
                title=title,
                source=str(md_file),
                content=content,
                category=self._detect_category(md_file.name),
                last_updated=md_file.stat().st_mtime,
            )
            self.pages.append(page)
            count += 1

        return count

    def generate(self) -> Dict[str, Any]:
        """Generate documentation site."""
        # Organize by category
        for page in self.pages:
            category = page.category
            if category not in self.sections:
                self.sections[category] = DocSection(title=category.title())
            self.sections[category].pages.append(page)

        # Generate index
        index = {
            "title": "APEX Documentation",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sections": {},
            "total_pages": len(self.pages),
        }

        for name, section in self.sections.items():
            index["sections"][name] = section.to_dict()

        # Write index
        index_file = self.docs_dir / "index.json"
        index_file.write_text(json.dumps(index, indent=2))

        # Generate HTML
        html = self._generate_html()
        html_file = self.docs_dir / "index.html"
        html_file.write_text(html)

        # Generate markdown index
        md = self._generate_markdown()
        md_file = self.docs_dir / "INDEX.md"
        md_file.write_text(md)

        return index

    def search(self, query: str) -> List[DocPage]:
        """Search documentation."""
        results = []
        query_lower = query.lower()

        for page in self.pages:
            score = 0.0
            if query_lower in page.title.lower():
                score += 1.0
            if query_lower in page.content.lower():
                score += 0.5

            if score > 0:
                results.append(page)

        return results

    def get_page(self, title: str) -> Optional[DocPage]:
        """Get a page by title."""
        for page in self.pages:
            if page.title.lower() == title.lower():
                return page
        return None

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from markdown content."""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None

    def _detect_category(self, name: str) -> str:
        """Detect category from name."""
        name_lower = name.lower()

        if "pipeline" in name_lower or "forge" in name_lower:
            return "pipelines"
        if "runtime" in name_lower or "state" in name_lower:
            return "runtime"
        if "test" in name_lower:
            return "testing"
        if "deploy" in name_lower or "ci" in name_lower:
            return "deployment"
        if "skill" in name_lower or "mastery" in name_lower:
            return "skills"
        if "security" in name_lower:
            return "security"

        return "general"

    def _generate_html(self) -> str:
        """Generate HTML index."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>APEX Documentation</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .section { margin: 20px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .section h2 { margin-top: 0; }
        .page { margin: 10px 0; padding: 5px; }
        .page a { color: #0066cc; text-decoration: none; }
        .page a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>APEX Documentation</h1>
"""
        for name, section in self.sections.items():
            html += f'    <div class="section">\n'
            html += f'        <h2>{section.title}</h2>\n'
            for page in section.pages:
                html += f'        <div class="page"><a href="{page.source}">{page.title}</a></div>\n'
            html += f'    </div>\n'

        html += "</body>\n</html>"
        return html

    def _generate_markdown(self) -> str:
        """Generate markdown index."""
        md = "# APEX Documentation\n\n"
        md += f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += f"Total pages: {len(self.pages)}\n\n"

        for name, section in self.sections.items():
            md += f"## {section.title}\n\n"
            for page in section.pages:
                md += f"- [{page.title}]({page.source})\n"
            md += "\n"

        return md

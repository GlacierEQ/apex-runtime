#!/usr/bin/env python3
"""
CI/CD Workflow Generator — GitHub Actions Auto-Test on Push
Generates GitHub Actions workflows for repositories.

Usage:
    from ci_generator import CIGenerator

    gen = CIGenerator()
    workflows = gen.generate("hyper-pipeline", ["python", "tests"])
    gen.write_workflows(Path(".github/workflows"), workflows)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class CIWorkflow:
    """A GitHub Actions workflow."""
    name: str
    filename: str
    content: str
    triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "filename": self.filename,
            "triggers": self.triggers,
        }


class CIGenerator:
    """Generates GitHub Actions workflows."""

    def generate(self, repo_name: str, features: List[str]) -> List[CIWorkflow]:
        """Generate workflows for a repository."""
        workflows = []

        # Always add CI workflow
        workflows.append(self._generate_ci(repo_name, features))

        # Add deploy workflow if requested
        if "deploy" in features:
            workflows.append(self._generate_deploy(repo_name))

        # Add release workflow if requested
        if "release" in features:
            workflows.append(self._generate_release(repo_name))

        return workflows

    def _generate_ci(self, repo_name: str, features: List[str]) -> CIWorkflow:
        """Generate CI workflow."""
        content = f"""name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt 2>/dev/null || true
          pip install pytest pytest-asyncio hypothesis

      - name: Run tests
        run: |
          pytest tests/ -v --tb=short

      - name: Run linter
        run: |
          pip install ruff
          ruff check . || true
"""

        return CIWorkflow(
            name="CI",
            filename="ci.yml",
            content=content,
            triggers=["push", "pull_request"],
        )

    def _generate_deploy(self, repo_name: str) -> CIWorkflow:
        """Generate deploy workflow."""
        content = f"""name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy
        run: |
          echo "Deploy {repo_name}"
          # Add deployment steps here
"""

        return CIWorkflow(
            name="Deploy",
            filename="deploy.yml",
            content=content,
            triggers=["push"],
        )

    def _generate_release(self, repo_name: str) -> CIWorkflow:
        """Generate release workflow."""
        content = f"""name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        with:
          tag_name: ${{{{ github.ref }}}}
          release_name: Release ${{{{ github.ref }}}}
          draft: false
          prerelease: false
"""

        return CIWorkflow(
            name="Release",
            filename="release.yml",
            content=content,
            triggers=["push_tags"],
        )

    def write_workflows(self, output_dir: Path, workflows: List[CIWorkflow]) -> List[Path]:
        """Write workflow files to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)
        files = []

        for workflow in workflows:
            filepath = output_dir / workflow.filename
            filepath.write_text(workflow.content)
            files.append(filepath)

        return files

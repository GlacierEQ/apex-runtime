#!/usr/bin/env python3
"""
Monitoring — Health Checks and Alerts
Monitors repos, services, and system health.

Usage:
    from monitoring import HealthMonitor

    monitor = HealthMonitor("~/.apex/monitoring")
    monitor.check_repo("/path/to/repo")
    report = monitor.get_report()
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """A single health check."""
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass
class HealthReport:
    """Aggregated health report."""
    status: HealthStatus
    checks: List[HealthCheck]
    timestamp: float
    uptime: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "checks": [c.to_dict() for c in self.checks],
            "timestamp": self.timestamp,
            "uptime": self.uptime,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Health Report",
            "",
            f"**Status:** {self.status.value.upper()}",
            f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))}",
            "",
            "## Checks",
            "",
        ]
        for check in self.checks:
            status_icon = {
                HealthStatus.HEALTHY: "✓",
                HealthStatus.WARNING: "⚠",
                HealthStatus.CRITICAL: "✗",
                HealthStatus.UNKNOWN: "?",
            }.get(check.status, "?")
            lines.append(f"- {status_icon} **{check.name}**: {check.message}")
        return "\n".join(lines)


class HealthMonitor:
    """Health monitoring system."""

    def __init__(self, monitor_dir: str = "~/.apex/monitoring") -> None:
        self.monitor_dir = Path(monitor_dir).expanduser()
        self.monitor_dir.mkdir(parents=True, exist_ok=True)
        self.reports_file = self.monitor_dir / "reports.jsonl"
        self._start_time = time.time()

    def check_repo(self, repo_path: str) -> List[HealthCheck]:
        """Check health of a repository."""
        checks = []
        path = Path(repo_path)

        # Check if directory exists
        if not path.exists():
            checks.append(HealthCheck(
                name="exists",
                status=HealthStatus.CRITICAL,
                message=f"Repository not found: {repo_path}",
                timestamp=time.time(),
            ))
            return checks

        checks.append(HealthCheck(
            name="exists",
            status=HealthStatus.HEALTHY,
            message="Repository exists",
            timestamp=time.time(),
        ))

        # Check git status
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip():
                checks.append(HealthCheck(
                    name="git_clean",
                    status=HealthStatus.WARNING,
                    message=f"Uncommitted changes: {len(result.stdout.strip().splitlines())} files",
                    timestamp=time.time(),
                ))
            else:
                checks.append(HealthCheck(
                    name="git_clean",
                    status=HealthStatus.HEALTHY,
                    message="Working directory clean",
                    timestamp=time.time(),
                ))
        except Exception as e:
            checks.append(HealthCheck(
                name="git_clean",
                status=HealthStatus.UNKNOWN,
                message=f"Git check failed: {e}",
                timestamp=time.time(),
            ))

        # Check for tests
        tests_dir = path / "tests"
        if tests_dir.exists():
            test_files = list(tests_dir.glob("test_*.py"))
            checks.append(HealthCheck(
                name="tests_exist",
                status=HealthStatus.HEALTHY if test_files else HealthStatus.WARNING,
                message=f"Found {len(test_files)} test files",
                timestamp=time.time(),
                details={"test_files": [str(f.name) for f in test_files]},
            ))
        else:
            checks.append(HealthCheck(
                name="tests_exist",
                status=HealthStatus.WARNING,
                message="No tests directory found",
                timestamp=time.time(),
            ))

        # Check for README
        readme = path / "README.md"
        checks.append(HealthCheck(
            name="readme_exists",
            status=HealthStatus.HEALTHY if readme.exists() else HealthStatus.WARNING,
            message="README.md exists" if readme.exists() else "No README.md",
            timestamp=time.time(),
        ))

        return checks

    def check_all_repos(self, repo_paths: List[str]) -> HealthReport:
        """Check health of all repos."""
        all_checks = []
        for path in repo_paths:
            checks = self.check_repo(path)
            all_checks.extend(checks)

        # Determine overall status
        if any(c.status == HealthStatus.CRITICAL for c in all_checks):
            status = HealthStatus.CRITICAL
        elif any(c.status == HealthStatus.WARNING for c in all_checks):
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        report = HealthReport(
            status=status,
            checks=all_checks,
            timestamp=time.time(),
            uptime=time.time() - self._start_time,
        )

        # Save report
        self._save_report(report)
        return report

    def _save_report(self, report: HealthReport) -> None:
        """Save report to disk."""
        with open(self.reports_file, "a") as f:
            f.write(json.dumps(report.to_dict(), default=str) + "\n")

    def get_report(self, limit: int = 10) -> Optional[HealthReport]:
        """Get latest health report."""
        if not self.reports_file.exists():
            return None

        lines = self.reports_file.read_text().strip().split("\n")
        if not lines:
            return None

        latest = json.loads(lines[-1])
        return HealthReport(
            status=HealthStatus(latest["status"]),
            checks=[HealthCheck(**c) for c in latest["checks"]],
            timestamp=latest["timestamp"],
            uptime=latest.get("uptime", 0),
        )

    def get_history(self, limit: int = 50) -> List[HealthReport]:
        """Get health history."""
        if not self.reports_file.exists():
            return []

        reports = []
        lines = self.reports_file.read_text().strip().split("\n")
        for line in lines[-limit:]:
            if line:
                data = json.loads(line)
                reports.append(HealthReport(
                    status=HealthStatus(data["status"]),
                    checks=[HealthCheck(**c) for c in data["checks"]],
                    timestamp=data["timestamp"],
                    uptime=data.get("uptime", 0),
                ))
        return reports

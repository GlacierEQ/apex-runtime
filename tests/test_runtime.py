#!/usr/bin/env python3
"""
Tests for Apex Runtime — State, CI, Connectors, Search, Monitoring
"""

import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_store import StateStore, StateEntry
from ci_generator import CIGenerator, CIWorkflow
from connector_runtime import (
    ConnectorRuntime, BaseConnector, GitHubConnector, FilesystemConnector,
    ConnectorStatus, ConnectorInfo,
)
from search_engine import SearchEngine, SearchResult, IndexEntry
from monitoring import HealthMonitor, HealthCheck, HealthReport, HealthStatus


# ─── State Store Tests ───────────────────────────────────────────────────────

class TestStateStore:
    def test_set_and_get(self, tmp_path):
        store = StateStore(str(tmp_path / "state"))
        store.set("key1", "value1")
        assert store.get("key1") == "value1"

    def test_get_default(self, tmp_path):
        store = StateStore(str(tmp_path / "state"))
        assert store.get("missing", "default") == "default"

    def test_delete(self, tmp_path):
        store = StateStore(str(tmp_path / "state"))
        store.set("key1", "value1")
        assert store.delete("key1") is True
        assert store.get("key1") is None

    def test_keys(self, tmp_path):
        store = StateStore(str(tmp_path / "state"))
        store.set("a", 1)
        store.set("b", 2)
        assert set(store.keys()) == {"a", "b"}

    def test_history(self, tmp_path):
        store = StateStore(str(tmp_path / "state"))
        store.set("a", 1)
        store.set("b", 2)
        history = store.history()
        assert len(history) == 2

    def test_search(self, tmp_path):
        store = StateStore(str(tmp_path / "state"))
        store.set("mcp_server", "running")
        store.set("test_suite", "passing")
        results = store.search("mcp")
        assert len(results) == 1

    def test_export_import(self, tmp_path):
        store = StateStore(str(tmp_path / "state"))
        store.set("key1", "value1")
        exported = store.export()

        store2 = StateStore(str(tmp_path / "state2"))
        store2.import_state(exported)
        assert store2.get("key1") == "value1"


# ─── CI Generator Tests ─────────────────────────────────────────────────────

class TestCIGenerator:
    def test_generate_ci(self):
        gen = CIGenerator()
        workflows = gen.generate("test-repo", ["python", "tests"])
        assert len(workflows) == 1
        assert workflows[0].filename == "ci.yml"

    def test_generate_with_deploy(self):
        gen = CIGenerator()
        workflows = gen.generate("test-repo", ["python", "deploy"])
        assert len(workflows) == 2

    def test_write_workflows(self, tmp_path):
        gen = CIGenerator()
        workflows = gen.generate("test-repo", ["python"])
        files = gen.write_workflows(tmp_path, workflows)
        assert len(files) == 1
        assert files[0].exists()

    def test_workflow_content(self):
        gen = CIGenerator()
        workflows = gen.generate("test-repo", ["python"])
        assert "pytest" in workflows[0].content
        assert "actions/checkout" in workflows[0].content


# ─── Connector Runtime Tests ────────────────────────────────────────────────

class TestBaseConnector:
    def test_register_tool(self):
        connector = BaseConnector("test", "Test connector")
        connector.register_tool("hello", "Say hello", lambda args: "hi")
        assert len(connector._tools) == 1
        assert connector._tools[0]["name"] == "hello"

    def test_health_check(self):
        connector = BaseConnector("test", "Test connector")
        assert connector.health_check() == ConnectorStatus.HEALTHY


class TestGitHubConnector:
    def test_tools_registered(self):
        connector = GitHubConnector()
        assert len(connector._tools) == 2

    def test_info(self):
        connector = GitHubConnector()
        info = connector.get_info()
        assert info.name == "github"
        assert info.status == ConnectorStatus.HEALTHY


class TestFilesystemConnector:
    def test_tools_registered(self):
        connector = FilesystemConnector()
        assert len(connector._tools) == 3


class TestConnectorRuntime:
    def test_register_connector(self):
        runtime = ConnectorRuntime()
        connector = BaseConnector("test", "Test connector")
        runtime.register("test", connector)
        assert "test" in runtime.connectors

    def test_list_connectors(self):
        runtime = ConnectorRuntime()
        runtime.register("test", BaseConnector("test"))
        connectors = runtime.list_connectors()
        assert len(connectors) == 1

    def test_list_tools(self):
        runtime = ConnectorRuntime()
        connector = BaseConnector("test")
        connector.register_tool("tool1", "Tool 1", lambda args: None)
        runtime.register("test", connector)
        tools = runtime.list_tools()
        assert len(tools) == 1

    def test_health_check(self):
        runtime = ConnectorRuntime()
        runtime.register("test", BaseConnector("test"))
        report = runtime.health_check()
        assert report["status"] == "healthy"


# ─── Search Engine Tests ─────────────────────────────────────────────────────

class TestSearchEngine:
    def test_index_file(self, tmp_path):
        engine = SearchEngine(str(tmp_path / "index"))
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        result = engine.index_single_file(test_file)
        assert result is True

    def test_index_directory(self, tmp_path):
        engine = SearchEngine(str(tmp_path / "index"))
        (tmp_path / "a.py").write_text("def a(): pass")
        (tmp_path / "b.py").write_text("class B: pass")

        count = engine.index_directory(tmp_path)
        assert count == 2

    def test_search(self, tmp_path):
        engine = SearchEngine(str(tmp_path / "index"))
        test_file = tmp_path / "mcp_server.py"
        test_file.write_text("def create_server(): pass")
        engine.index_single_file(test_file)

        results = engine.search("server")
        assert len(results) > 0

    def test_search_by_type(self, tmp_path):
        engine = SearchEngine(str(tmp_path / "index"))
        (tmp_path / "test_a.py").write_text("def test(): pass")
        (tmp_path / "source.py").write_text("def func(): pass")
        engine.index_single_file(tmp_path / "test_a.py")
        engine.index_single_file(tmp_path / "source.py")

        tests = engine.search_by_type("test")
        assert len(tests) == 1

    def test_stats(self, tmp_path):
        engine = SearchEngine(str(tmp_path / "index"))
        (tmp_path / "a.py").write_text("def a(): pass")
        engine.index_single_file(tmp_path / "a.py")

        stats = engine.get_stats()
        assert stats["total_files"] == 1


# ─── Monitoring Tests ────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_to_dict(self):
        check = HealthCheck(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
            timestamp=1234567890,
        )
        d = check.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "healthy"


class TestHealthReport:
    def test_to_dict(self):
        report = HealthReport(
            status=HealthStatus.HEALTHY,
            checks=[],
            timestamp=1234567890,
        )
        d = report.to_dict()
        assert d["status"] == "healthy"

    def test_to_markdown(self):
        report = HealthReport(
            status=HealthStatus.WARNING,
            checks=[
                HealthCheck("test", HealthStatus.WARNING, "Warning", 1234567890),
            ],
            timestamp=1234567890,
        )
        md = report.to_markdown()
        assert "# Health Report" in md
        assert "WARNING" in md


class TestHealthMonitor:
    def test_check_repo(self, tmp_path):
        monitor = HealthMonitor(str(tmp_path / "monitor"))
        (tmp_path / "repo").mkdir()
        (tmp_path / "repo" / ".git").mkdir()
        (tmp_path / "repo" / "tests").mkdir()
        (tmp_path / "repo" / "README.md").write_text("# Test")

        checks = monitor.check_repo(str(tmp_path / "repo"))
        assert len(checks) >= 3

    def test_check_missing_repo(self, tmp_path):
        monitor = HealthMonitor(str(tmp_path / "monitor"))
        checks = monitor.check_repo("/nonexistent")
        assert checks[0].status == HealthStatus.CRITICAL

    def test_get_report(self, tmp_path):
        monitor = HealthMonitor(str(tmp_path / "monitor"))
        report = monitor.get_report()
        assert report is None  # No reports yet


# ─── Integration Tests ───────────────────────────────────────────────────────

class TestIntegration:
    def test_full_workflow(self, tmp_path):
        """Test complete runtime workflow."""
        # State persistence
        store = StateStore(str(tmp_path / "state"))
        store.set("current_task", "build MCP server")

        # Search indexing
        engine = SearchEngine(str(tmp_path / "index"))
        test_file = tmp_path / "mcp_server.py"
        test_file.write_text("def create_server(): pass")
        engine.index_single_file(test_file)

        # Health monitoring
        monitor = HealthMonitor(str(tmp_path / "monitor"))
        (tmp_path / "repo").mkdir()
        (tmp_path / "repo" / ".git").mkdir()
        checks = monitor.check_repo(str(tmp_path / "repo"))

        # Verify everything
        assert store.get("current_task") == "build MCP server"
        results = engine.search("server")
        assert len(results) > 0
        assert any(c.name == "exists" for c in checks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

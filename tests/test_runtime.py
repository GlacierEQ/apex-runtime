#!/usr/bin/env python3
"""
Tests for Apex Runtime — All 8 Engines
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
from error_recovery import RecoveryManager, Checkpoint, RecoveryAction
from doc_site import DocSite, DocPage, DocSection
from skill_registry import SkillRegistry, SkillInfo


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


# ─── Error Recovery Tests ────────────────────────────────────────────────────

class TestRecoveryManager:
    def test_checkpoint(self, tmp_path):
        recovery = RecoveryManager(str(tmp_path / "recovery"))
        cp = recovery.checkpoint("test_checkpoint")
        assert cp.id.startswith("cp_")
        assert cp.name == "test_checkpoint"

    def test_list_checkpoints(self, tmp_path):
        recovery = RecoveryManager(str(tmp_path / "recovery"))
        recovery.checkpoint("cp1")
        recovery.checkpoint("cp2")
        cps = recovery.list_checkpoints()
        assert len(cps) == 2

    def test_create_backup(self, tmp_path):
        recovery = RecoveryManager(str(tmp_path / "recovery"))
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        backup = recovery.create_backup(str(test_file))
        assert backup is not None
        assert Path(backup).exists()

    def test_rollback(self, tmp_path):
        recovery = RecoveryManager(str(tmp_path / "recovery"))
        cp = recovery.checkpoint("before_change")
        result = recovery.rollback(cp.id)
        assert result is True

    def test_history(self, tmp_path):
        recovery = RecoveryManager(str(tmp_path / "recovery"))
        recovery.checkpoint("test")
        history = recovery.get_history()
        assert len(history) >= 1

    def test_safe_execute(self, tmp_path):
        recovery = RecoveryManager(str(tmp_path / "recovery"))

        def good_func():
            return "success"

        result = recovery.safe_execute(good_func, "test_good")
        assert result == "success"

    def test_safe_execute_rollback(self, tmp_path):
        recovery = RecoveryManager(str(tmp_path / "recovery"))

        def bad_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            recovery.safe_execute(bad_func, "test_bad")
        history = recovery.get_history()
        assert any(a.action == "safe_execute_failed" for a in history)


# ─── Documentation Site Tests ────────────────────────────────────────────────

class TestDocSite:
    def test_add_repo(self, tmp_path):
        site = DocSite(str(tmp_path / "docs"))
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# My Repo\n\nDescription here.")

        count = site.add_repo(str(repo))
        assert count == 1

    def test_generate(self, tmp_path):
        site = DocSite(str(tmp_path / "docs"))
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Test\n\nContent.")

        site.add_repo(str(repo))
        result = site.generate()
        assert result["total_pages"] == 1
        assert (tmp_path / "docs" / "index.html").exists()
        assert (tmp_path / "docs" / "INDEX.md").exists()

    def test_search(self, tmp_path):
        site = DocSite(str(tmp_path / "docs"))
        (tmp_path / "README.md").write_text("# MCP Server\n\nBuild MCP tools.")
        site.add_repo(str(tmp_path))

        results = site.search("MCP")
        assert len(results) > 0

    def test_categories(self, tmp_path):
        site = DocSite(str(tmp_path / "docs"))
        repo = tmp_path / "pipeline-repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Pipeline Forge\n\nBuild pipelines.")
        site.add_repo(str(repo))
        site.generate()

        categories = list(site.sections.keys())
        assert "pipelines" in categories


# ─── Skill Registry Tests ────────────────────────────────────────────────────

class TestSkillRegistry:
    def test_register(self, tmp_path):
        registry = SkillRegistry(str(tmp_path / "skills"))
        skill_file = tmp_path / "test_skill.md"
        skill_file.write_text("# Test Skill\n\nDescription of skill.\n\ntags: python, testing\ntrigger: when testing")

        skill = registry.register(str(skill_file))
        assert skill.name == "test_skill"
        assert "python" in skill.tags

    def test_list_all(self, tmp_path):
        registry = SkillRegistry(str(tmp_path / "skills"))
        (tmp_path / "a.md").write_text("# Skill A\n\nDesc A.")
        (tmp_path / "b.md").write_text("# Skill B\n\nDesc B.")
        registry.register(str(tmp_path / "a.md"))
        registry.register(str(tmp_path / "b.md"))

        skills = registry.list_all()
        assert len(skills) == 2

    def test_search(self, tmp_path):
        registry = SkillRegistry(str(tmp_path / "skills"))
        (tmp_path / "mcp_skill.md").write_text("# MCP Connector\n\nConnect to MCP servers.")
        registry.register(str(tmp_path / "mcp_skill.md"))

        results = registry.search("MCP")
        assert len(results) > 0

    def test_unregister(self, tmp_path):
        registry = SkillRegistry(str(tmp_path / "skills"))
        (tmp_path / "skill.md").write_text("# Skill\n\nDesc.")
        registry.register(str(tmp_path / "skill.md"))

        assert registry.unregister("skill") is True
        assert registry.get("skill") is None

    def test_stats(self, tmp_path):
        registry = SkillRegistry(str(tmp_path / "skills"))
        (tmp_path / "skill.md").write_text("# Skill\n\nDesc.")
        registry.register(str(tmp_path / "skill.md"))

        stats = registry.get_stats()
        assert stats["total_skills"] == 1

    def test_categories(self, tmp_path):
        registry = SkillRegistry(str(tmp_path / "skills"))
        (tmp_path / "pipeline.md").write_text("# Pipeline Skill\n\nBuild pipelines.")
        (tmp_path / "test.md").write_text("# Test Skill\n\nRun tests.")
        registry.register(str(tmp_path / "pipeline.md"))
        registry.register(str(tmp_path / "test.md"))

        categories = registry.get_categories()
        assert "pipelines" in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Apex Runtime — CLI Interface
State, CI, Connectors, Search, Monitoring

Usage:
    python3 runtime.py state set key value
    python3 runtime.py state get key
    python3 runtime.py ci generate --repo /path
    python3 runtime.py connector list
    python3 runtime.py search "query"
    python3 runtime.py monitor --repos /path1,/path2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

from state_store import StateStore
from ci_generator import CIGenerator
from connector_runtime import ConnectorRuntime, GitHubConnector, FilesystemConnector
from search_engine import SearchEngine
from monitoring import HealthMonitor


VERSION = "1.0.0"
BASE_DIR = Path.home() / ".apex"


def cmd_state(args: argparse.Namespace) -> int:
    """State persistence commands."""
    store = StateStore(str(BASE_DIR / "state"))

    if args.state_action == "set":
        store.set(args.key, args.value)
        print(f"Set {args.key} = {args.value}")
    elif args.state_action == "get":
        value = store.get(args.key)
        print(f"{args.key} = {value}")
    elif args.state_action == "delete":
        store.delete(args.key)
        print(f"Deleted {args.key}")
    elif args.state_action == "list":
        for key in store.keys():
            print(f"  {key} = {store.get(key)}")
    elif args.state_action == "history":
        for entry in store.history(limit=args.limit):
            print(f"  [{entry.key}] {entry.value}")

    return 0


def cmd_ci(args: argparse.Namespace) -> int:
    """CI/CD commands."""
    gen = CIGenerator()

    if args.ci_action == "generate":
        repo_name = Path(args.repo).name
        features = [f.strip() for f in args.features.split(",")]
        workflows = gen.generate(repo_name, features)

        output_dir = Path(args.repo) / ".github" / "workflows"
        files = gen.write_workflows(output_dir, workflows)

        print(f"Generated {len(files)} workflows:")
        for f in files:
            print(f"  ✓ {f}")
    elif args.ci_action == "list":
        print("Available features: python, tests, deploy, release")

    return 0


def cmd_connector(args: argparse.Namespace) -> int:
    """Connector commands."""
    runtime = ConnectorRuntime()

    # Register built-in connectors
    runtime.register("github", GitHubConnector())
    runtime.register("filesystem", FilesystemConnector())

    if args.connector_action == "list":
        connectors = runtime.list_connectors()
        print("\nConnectors:")
        for c in connectors:
            print(f"  {c.name}: {c.description} [{c.status.value}]")
        print(f"\nTotal: {len(connectors)}")
    elif args.connector_action == "tools":
        tools = runtime.list_tools()
        print("\nTools:")
        for t in tools:
            print(f"  {t['connector']}/{t['name']}: {t['description']}")
        print(f"\nTotal: {len(tools)}")
    elif args.connector_action == "health":
        report = runtime.health_check()
        print(f"\nStatus: {report['status']}")
        print(f"Uptime: {report['uptime']:.0f}s")
        for name, info in report["connectors"].items():
            print(f"  {name}: {info['status']}")

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search commands."""
    engine = SearchEngine(str(BASE_DIR / "index"))

    if args.search_action == "index":
        repo_path = Path(args.repo)
        result = engine.index_repo(str(repo_path))
        print(f"Indexed {result['files_indexed']} files in {result['repo']}")
        print(f"Duration: {result['duration_ms']:.0f}ms")
    elif args.search_action == "query":
        results = engine.search(args.query, limit=args.limit)
        print(f"\nResults for '{args.query}':")
        for r in results:
            print(f"  [{r.score:.2f}] {r.name} ({r.type})")
            print(f"         {r.path}")
        print(f"\nTotal: {len(results)}")
    elif args.search_action == "stats":
        stats = engine.get_stats()
        print(f"\nIndex Stats:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Types: {stats['types']}")

    return 0


def cmd_monitor(args: argparse.Namespace) -> int:
    """Monitoring commands."""
    monitor = HealthMonitor(str(BASE_DIR / "monitoring"))

    if args.monitor_action == "check":
        repos = [r.strip() for r in args.repos.split(",")]
        report = monitor.check_all_repos(repos)
        print(report.to_markdown())
    elif args.monitor_action == "history":
        reports = monitor.get_history(limit=args.limit)
        for r in reports:
            print(f"  [{r.status.value}] {r.timestamp}")
    elif args.monitor_action == "latest":
        report = monitor.get_report()
        if report:
            print(report.to_markdown())
        else:
            print("No reports yet")

    return 0


def cmd_recovery(args: argparse.Namespace) -> int:
    """Recovery commands."""
    recovery = RecoveryManager(str(BASE_DIR / "recovery"))

    if args.recovery_action == "checkpoints":
        cps = recovery.list_checkpoints()
        print("\nCheckpoints:")
        for cp in cps:
            print(f"  {cp.id}: {cp.name}")
        print(f"\nTotal: {len(cps)}")
    elif args.recovery_action == "checkpoint":
        cp = recovery.checkpoint(args.name)
        print(f"Created checkpoint: {cp.id} ({cp.name})")
    elif args.recovery_action == "rollback":
        if recovery.rollback(args.id):
            print(f"Rolled back to: {args.id}")
        else:
            print(f"Failed to rollback to: {args.id}")
    elif args.recovery_action == "history":
        history = recovery.get_history()
        print("\nRecovery History:")
        for action in history:
            status = "✓" if action.success else "✗"
            print(f"  {status} [{action.action}] {action.details}")

    return 0


def cmd_docs(args: argparse.Namespace) -> int:
    """Documentation commands."""
    site = DocSite(str(BASE_DIR / "docs"))

    if args.docs_action == "add":
        count = site.add_repo(args.repo)
        print(f"Added {count} pages from {args.repo}")
    elif args.docs_action == "generate":
        result = site.generate()
        print(f"Generated documentation site:")
        print(f"  Pages: {result['total_pages']}")
        print(f"  Sections: {len(result['sections'])}")
    elif args.docs_action == "search":
        results = site.search(args.query)
        print(f"\nResults for '{args.query}':")
        for page in results:
            print(f"  {page.title} ({page.category})")
        print(f"\nTotal: {len(results)}")

    return 0


def cmd_skills(args: argparse.Namespace) -> int:
    """Skill registry commands."""
    registry = SkillRegistry(str(BASE_DIR / "skills"))

    if args.skills_action == "register":
        skill = registry.register(args.path)
        print(f"Registered: {skill.name}")
        print(f"  Category: {skill.category}")
        print(f"  Tags: {', '.join(skill.tags)}")
    elif args.skills_action == "list":
        skills = registry.list_all()
        print("\nRegistered Skills:")
        for skill in skills:
            print(f"  {skill.name} ({skill.category})")
        print(f"\nTotal: {len(skills)}")
    elif args.skills_action == "search":
        results = registry.search(args.query)
        print(f"\nResults for '{args.query}':")
        for skill in results:
            print(f"  {skill.name}: {skill.description[:50]}")
        print(f"\nTotal: {len(results)}")
    elif args.skills_action == "stats":
        stats = registry.get_stats()
        print(f"\nRegistry Stats:")
        print(f"  Total skills: {stats['total_skills']}")
        print(f"  Categories: {stats['categories']}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Apex Runtime v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # State commands
    state = sub.add_parser("state", help="State persistence")
    state_sub = state.add_subparsers(dest="state_action")
    state_set = state_sub.add_parser("set", help="Set state")
    state_set.add_argument("key", help="Key")
    state_set.add_argument("value", help="Value")
    state_get = state_sub.add_parser("get", help="Get state")
    state_get.add_argument("key", help="Key")
    state_del = state_sub.add_parser("delete", help="Delete state")
    state_del.add_argument("key", help="Key")
    state_sub.add_parser("list", help="List all state")
    state_hist = state_sub.add_parser("history", help="Show history")
    state_hist.add_argument("--limit", type=int, default=50)

    # CI commands
    ci = sub.add_parser("ci", help="CI/CD workflows")
    ci_sub = ci.add_subparsers(dest="ci_action")
    ci_gen = ci_sub.add_parser("generate", help="Generate workflows")
    ci_gen.add_argument("--repo", required=True, help="Repository path")
    ci_gen.add_argument("--features", default="python,tests", help="Features")
    ci_sub.add_parser("list", help="List features")

    # Connector commands
    conn = sub.add_parser("connector", help="Connector runtime")
    conn_sub = conn.add_subparsers(dest="connector_action")
    conn_sub.add_parser("list", help="List connectors")
    conn_sub.add_parser("tools", help="List tools")
    conn_sub.add_parser("health", help="Health check")

    # Search commands
    search = sub.add_parser("search", help="Search engine")
    search_sub = search.add_subparsers(dest="search_action")
    search_idx = search_sub.add_parser("index", help="Index repository")
    search_idx.add_argument("--repo", required=True, help="Repository path")
    search_q = search_sub.add_parser("query", help="Search query")
    search_q.add_argument("query", help="Search query")
    search_q.add_argument("--limit", type=int, default=20)
    search_sub.add_parser("stats", help="Index statistics")

    # Monitor commands
    monitor = sub.add_parser("monitor", help="Health monitoring")
    mon_sub = monitor.add_subparsers(dest="monitor_action")
    mon_check = mon_sub.add_parser("check", help="Check repositories")
    mon_check.add_argument("--repos", required=True, help="Repository paths (comma-separated)")
    mon_hist = mon_sub.add_parser("history", help="Check history")
    mon_hist.add_argument("--limit", type=int, default=10)
    mon_sub.add_parser("latest", help="Latest report")

    # Recovery commands
    recovery = sub.add_parser("recovery", help="Error recovery")
    rec_sub = recovery.add_subparsers(dest="recovery_action")
    rec_sub.add_parser("checkpoints", help="List checkpoints")
    rec_cp = rec_sub.add_parser("checkpoint", help="Create checkpoint")
    rec_cp.add_argument("name", help="Checkpoint name")
    rec_rb = rec_sub.add_parser("rollback", help="Rollback to checkpoint")
    rec_rb.add_argument("id", help="Checkpoint ID")
    rec_sub.add_parser("history", help="Recovery history")

    # Docs commands
    docs = sub.add_parser("docs", help="Documentation site")
    docs_sub = docs.add_subparsers(dest="docs_action")
    docs_add = docs_sub.add_parser("add", help="Add repository docs")
    docs_add.add_argument("--repo", required=True, help="Repository path")
    docs_sub.add_parser("generate", help="Generate site")
    docs_search = docs_sub.add_parser("search", help="Search docs")
    docs_search.add_argument("query", help="Search query")

    # Skills commands
    skills = sub.add_parser("skills", help="Skill registry")
    skills_sub = skills.add_subparsers(dest="skills_action")
    skills_reg = skills_sub.add_parser("register", help="Register skill")
    skills_reg.add_argument("path", help="Skill file or directory")
    skills_sub.add_parser("list", help="List all skills")
    skills_search = skills_sub.add_parser("search", help="Search skills")
    skills_search.add_argument("query", help="Search query")
    skills_sub.add_parser("stats", help="Registry stats")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "state": cmd_state,
        "ci": cmd_ci,
        "connector": cmd_connector,
        "search": cmd_search,
        "monitor": cmd_monitor,
        "recovery": cmd_recovery,
        "docs": cmd_docs,
        "skills": cmd_skills,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

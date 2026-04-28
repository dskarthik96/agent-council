#!/usr/bin/env python3
"""
Council — run.py

Usage:
  python run.py                              interactive mode
  python run.py "Your question here"         single question
  python run.py --memory list                list saved memories
  python run.py --memory show <key>          show a saved memory
  python run.py --kb list                    list knowledge base entries
  python run.py --kb add <name> <file.md>    add a KB entry
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).parent


# ── bootstrap ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg_path = BASE / "config.yaml"
    if not cfg_path.exists():
        print("  No config.yaml found. Run: python setup.py")
        sys.exit(1)
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def build_leader(cfg: dict):
    from skills import REGISTRY
    from leader.agent import LeaderAgent
    from core.context import SharedContext
    from core.models import detect_ollama
    from memory.session import SessionMemory
    from memory.store import MemoryStore

    # Detect local models at startup
    local_cfg = cfg.get("local_models", {})
    local_models: list[str] = []
    if local_cfg.get("enabled"):
        local_models = detect_ollama() or local_cfg.get("available", [])

    # Build skills from config
    skills = {}
    for name, agent_cfg in cfg.get("agents", {}).items():
        skill_key = agent_cfg.get("skill", name)
        cls = REGISTRY.get(skill_key)
        if cls is None:
            print(f"  Warning: unknown skill '{skill_key}', skipping")
            continue
        skills[name] = cls(
            model=agent_cfg.get("model") or (
                local_models[0]
                if local_models and cls.default_model.startswith("claude-haiku")
                else None
            ),
            extra_instructions=agent_cfg.get("extra_instructions", ""),
        )

    project_ctx = cfg.get("project", {}).get("context", "")
    shared = SharedContext(BASE / cfg["knowledge"]["path"], project_context=project_ctx)
    memory = SessionMemory(max_exchanges=cfg["memory"]["max_session_exchanges"])
    store = MemoryStore(BASE / cfg["memory"]["long_term_path"])

    return LeaderAgent(
        skills=skills,
        shared_context=shared,
        memory=memory,
        store=store,
        model=cfg.get("leader", {}).get("model", "claude-sonnet-4-6"),
        local_models=local_models,
    ), store, shared


# ── single question ──────────────────────────────────────────────────────────

def run_once(question: str, leader, store, shared) -> None:
    from ui.terminal import CouncilUI

    with CouncilUI(list(leader.skills.keys()), question) as ui:
        leader.ui = ui
        result = leader.decide(question)

    ui.print_result(result)


# ── interactive ──────────────────────────────────────────────────────────────

def run_interactive(leader, store, shared) -> None:
    from rich.console import Console
    console = Console()
    console.print("\n  [bold]Council[/bold] — interactive mode")
    console.print("  [dim]Commands: exit · memory save <key> · memory list · kb list[/dim]\n")

    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q or q.lower() in ("exit", "quit"):
            break

        if q.startswith("memory save "):
            key = q.split(" ", 2)[2]
            store.save(key, {"context": leader.memory.get_context()})
            print(f"  Saved to long-term memory as '{key}'\n")
            continue
        if q == "memory list":
            print(f"  {store.all_keys() or '(none)'}\n")
            continue
        if q == "kb list":
            print(f"  {shared.list_knowledge() or '(empty)'}\n")
            continue

        run_once(q, leader, store, shared)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]
    cfg = load_config()
    leader, store, shared = build_leader(cfg)

    if not args or args[0] == "--interactive":
        run_interactive(leader, store, shared)

    elif args[0] == "--memory":
        sub = args[1] if len(args) > 1 else ""
        if sub == "list":
            print(store.all_keys())
        elif sub == "show" and len(args) >= 3:
            data = store.load(args[2])
            print(json.dumps(data, indent=2) if data else "Not found")

    elif args[0] == "--kb":
        sub = args[1] if len(args) > 1 else ""
        if sub == "list":
            print(shared.list_knowledge())
        elif sub == "add" and len(args) >= 4:
            content = Path(args[3]).read_text(encoding="utf-8")
            shared.add_knowledge(args[2], content)
            print(f"Added '{args[2]}' to knowledge base")

    else:
        run_once(" ".join(args), leader, store, shared)


if __name__ == "__main__":
    main()

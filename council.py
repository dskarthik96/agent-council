#!/usr/bin/env python3
"""
Council — multi-agent decision system.

Usage:
  python council.py "What should I prioritise this week?"
  python council.py --interactive
  python council.py --memory list
  python council.py --memory show <key>
  python council.py --memory save <key>   (in interactive mode: type 'memory save <key>')
  python council.py --kb list
  python council.py --kb add <name> <file.md>
"""
import sys
import json
from pathlib import Path

import yaml

from core.agent import Agent
from core.kb import KnowledgeBase
from core.orchestrator import Orchestrator
from memory.session import SessionMemory
from memory.store import MemoryStore
from mcp.client import MCPClient

BASE = Path(__file__).parent


def load_config() -> dict:
    return yaml.safe_load((BASE / "config.yaml").read_text())


def build_council(config: dict) -> Orchestrator:
    agents = {
        name: Agent(name, cfg["model"], cfg["role"].strip())
        for name, cfg in config["agents"].items()
    }
    memory = SessionMemory(max_exchanges=config["memory"]["max_session_exchanges"])
    store = MemoryStore(BASE / config["memory"]["long_term_path"])
    kb = KnowledgeBase(BASE / config["knowledge"]["path"])
    mcp = MCPClient(config.get("mcp", {}).get("servers", []))
    if config.get("mcp", {}).get("servers"):
        mcp.connect()
    return Orchestrator(agents, memory, store, kb, mcp.to_anthropic_tools())


def print_result(result: dict) -> None:
    print(f"\n  Agents consulted: {', '.join(result['agents_consulted'])}")
    print("\n" + "─" * 64)
    for name, resp in result["perspectives"].items():
        print(f"\n  [{name.upper()}]\n{resp.strip()}")
        print("─" * 64)
    print(f"\n  DECISION\n{result['decision'].strip()}\n")


def run_interactive(council: Orchestrator) -> None:
    print("Council — interactive mode")
    print("Commands: 'exit'  'memory save <key>'  'memory list'  'kb list'\n")
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q or q.lower() in ("exit", "quit"):
            break

        # inline commands
        if q.startswith("memory save "):
            key = q.split(" ", 2)[2]
            council.store.save(key, {"context": council.memory.get_context()})
            print(f"  Saved to long-term memory as '{key}'\n")
            continue
        if q == "memory list":
            keys = council.store.all_keys()
            print(f"  Long-term memories: {keys or '(none)'}\n")
            continue
        if q == "kb list":
            entries = council.kb.list_entries()
            print(f"  Knowledge base: {entries or '(empty)'}\n")
            continue

        result = council.decide(q)
        print_result(result)


def main() -> None:
    args = sys.argv[1:]
    config = load_config()
    council = build_council(config)

    if not args or args[0] == "--interactive":
        run_interactive(council)

    elif args[0] == "--memory":
        sub = args[1] if len(args) > 1 else ""
        if sub == "list":
            print(council.store.all_keys())
        elif sub == "show" and len(args) >= 3:
            data = council.store.load(args[2])
            print(json.dumps(data, indent=2) if data else "Not found")
        else:
            print("Usage: --memory list | --memory show <key>")

    elif args[0] == "--kb":
        sub = args[1] if len(args) > 1 else ""
        if sub == "list":
            print(council.kb.list_entries())
        elif sub == "add" and len(args) >= 4:
            content = Path(args[3]).read_text()
            council.kb.add(args[2], content)
            print(f"Added '{args[2]}' to knowledge base")
        else:
            print("Usage: --kb list | --kb add <name> <file.md>")

    else:
        result = council.decide(" ".join(args))
        print_result(result)


if __name__ == "__main__":
    main()

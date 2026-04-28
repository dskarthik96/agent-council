#!/usr/bin/env python3
"""
Council setup wizard.

Run once to configure your council:
    python setup.py

Then use it:
    python run.py --interactive
    python run.py "Your question here"
"""
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).parent

SKILLS_AVAILABLE = {
    "strategist": "Long-term thinking, strategic risks and opportunities",
    "critic":     "Finds flaws, challenges assumptions, strongest counter-argument",
    "researcher": "Synthesises knowledge, surfaces information gaps",
    "executor":   "Concrete next steps, blockers, fastest path to done",
}


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def main() -> None:
    print("\n  Council Setup\n" + "─" * 40)

    # ── project ───────────────────────────────────────────────────────────────
    name = ask("Project name", "my-council")
    context = ask("One-line project context (helps agents give relevant answers)", "")

    # ── skills ────────────────────────────────────────────────────────────────
    print("\n  Available skills:")
    for k, v in SKILLS_AVAILABLE.items():
        print(f"    [{k:12}]  {v}")
    raw = ask("\n  Enable skills (comma-separated or 'all')", "all")
    if raw.lower() == "all":
        enabled = list(SKILLS_AVAILABLE)
    else:
        enabled = [s.strip() for s in raw.split(",") if s.strip() in SKILLS_AVAILABLE]
    if not enabled:
        enabled = list(SKILLS_AVAILABLE)

    # Per-skill customisation
    agents: dict = {}
    for skill in enabled:
        print(f"\n  [{skill}] Custom instructions (Enter to use default):")
        instructions = input("  > ").strip()
        agents[skill] = {"skill": skill, "extra_instructions": instructions}

    # ── models ────────────────────────────────────────────────────────────────
    print("\n  Model settings")
    leader_model = ask("  Leader model", "claude-sonnet-4-6")

    # ── local models ──────────────────────────────────────────────────────────
    print("\n  Checking for local Ollama models...", end="", flush=True)
    try:
        from core.models import detect_ollama
        local = detect_ollama()
    except Exception:
        local = []

    if local:
        print(f" found: {', '.join(local)}")
        use_local = ask("  Use local models for routing/compression (saves cost)", "y")
        local_enabled = use_local.lower() != "n"
    else:
        print(" none found")
        print("  (Install Ollama at ollama.com for free local inference on routing tasks)")
        local_enabled = False

    # ── write config ──────────────────────────────────────────────────────────
    config = {
        "project": {"name": name, "context": context},
        "leader":  {"model": leader_model},
        "agents":  agents,
        "local_models": {"enabled": local_enabled, "available": local},
        "memory":  {"max_session_exchanges": 10, "long_term_path": "memory/long_term"},
        "knowledge": {"path": "knowledge"},
        "mcp": {"servers": []},
    }

    (BASE / "config.yaml").write_text(
        yaml.dump(config, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    print("\n  config.yaml written")

    # Save project context to KB if provided
    if context:
        kb = BASE / "knowledge"
        kb.mkdir(exist_ok=True)
        (kb / "project-context.md").write_text(
            f"# {name}\n\n{context}\n", encoding="utf-8"
        )
        print("  Project context saved to knowledge/project-context.md")

    print(f"\n  Done. Run: python run.py --interactive\n")


if __name__ == "__main__":
    main()

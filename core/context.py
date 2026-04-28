"""
SharedContext — builds the one context block that ALL agents receive.

This is the primary cost lever: the shared block is written to Anthropic's
prompt cache once per session and read from cache on every subsequent agent call.
Instead of paying ~1000 input tokens per agent call, you pay for one write
and then near-zero for every read.
"""
from __future__ import annotations

from pathlib import Path


class SharedContext:
    def __init__(self, kb_path: str | Path, project_context: str = "") -> None:
        self.kb_path = Path(kb_path)
        self.project_context = project_context
        self.kb_path.mkdir(parents=True, exist_ok=True)

    def build(self, query: str = "", session_summary: str = "") -> str:
        """
        Assemble the shared context string.
        Called once per query; result is injected into every agent's system prompt.
        """
        parts: list[str] = []

        if self.project_context:
            parts.append(f"## Project Context\n{self.project_context}")

        kb = self._search_kb(query) if query else ""
        if kb:
            parts.append(f"## Relevant Knowledge\n{kb}")

        if session_summary:
            parts.append(f"## Session History\n{session_summary}")

        return "\n\n".join(parts)

    def _search_kb(self, query: str, max_snippets: int = 3) -> str:
        words = {w.lower() for w in query.split() if len(w) > 3}
        if not words:
            return ""

        scored: list[tuple[int, str, str]] = []
        for p in self.kb_path.glob("*.md"):
            content = p.read_text(encoding="utf-8")
            score = sum(1 for w in words if w in content.lower())
            if score > 0:
                scored.append((score, p.stem, content))

        scored.sort(reverse=True)
        return "\n\n".join(
            f"### {name}\n{content[:600].strip()}"
            for _, name, content in scored[:max_snippets]
        )

    def add_knowledge(self, name: str, content: str) -> None:
        (self.kb_path / f"{name}.md").write_text(content, encoding="utf-8")

    def list_knowledge(self) -> list[str]:
        return sorted(p.stem for p in self.kb_path.glob("*.md"))

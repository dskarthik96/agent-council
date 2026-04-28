from pathlib import Path


class KnowledgeBase:
    """File-based knowledge base. Drop .md files into the knowledge/ folder.
    search() does keyword scoring — no vector DB, zero infra."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, max_snippets: int = 3) -> str:
        query_words = {w.lower() for w in query.split() if len(w) > 3}
        if not query_words:
            return ""

        scored: list[tuple[int, str, str]] = []
        for p in self.path.glob("*.md"):
            content = p.read_text(encoding="utf-8")
            score = sum(1 for w in query_words if w in content.lower())
            if score > 0:
                scored.append((score, p.stem, content))

        scored.sort(reverse=True)
        snippets = [
            f"### [{name}]\n{content[:600].strip()}"
            for _, name, content in scored[:max_snippets]
        ]
        return "\n\n".join(snippets)

    def add(self, name: str, content: str) -> None:
        (self.path / f"{name}.md").write_text(content, encoding="utf-8")

    def list_entries(self) -> list[str]:
        return sorted(p.stem for p in self.path.glob("*.md"))

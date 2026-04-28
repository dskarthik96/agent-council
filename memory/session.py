import anthropic


class SessionMemory:
    """In-session context window. Auto-compresses with Haiku when it grows too long."""

    def __init__(self, max_exchanges: int = 10):
        self.exchanges: list[dict] = []
        self.summary = ""
        self.max_exchanges = max_exchanges
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def add(self, question: str, perspectives: dict, decision: str) -> None:
        self.exchanges.append({
            "q": question,
            "agents": list(perspectives.keys()),
            "decision": decision,
        })
        if len(self.exchanges) > self.max_exchanges:
            self._compress()

    def _compress(self) -> None:
        history = "\n".join(
            f"Q: {e['q']}\nDecision: {e['decision']}" for e in self.exchanges
        )
        resp = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"Summarise this decision history in 4 bullet points:\n{history}",
            }],
        )
        self.summary = resp.content[0].text
        self.exchanges = self.exchanges[-3:]  # keep last 3 verbatim

    def get_context(self) -> str:
        parts: list[str] = []
        if self.summary:
            parts.append(f"Prior session summary:\n{self.summary}")
        for e in self.exchanges:
            parts.append(f"Q: {e['q']}\nDecision: {e['decision']}")
        return "\n\n".join(parts)

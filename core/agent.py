import anthropic


class Agent:
    """A single council member. Config-driven — model and role come from config.yaml."""

    def __init__(self, name: str, model: str, system: str):
        self.name = name
        self.model = model
        self.system = system
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def think(self, question: str, context: str = "", kb_snippets: str = "") -> str:
        """Call this agent with a question. Returns its response text."""
        system_text = self.system
        if kb_snippets:
            system_text += f"\n\n---\n## Relevant Knowledge\n{kb_snippets}"

        messages: list[dict] = []
        if context:
            messages += [
                {"role": "user", "content": f"<context>\n{context}\n</context>"},
                {"role": "assistant", "content": "Context noted."},
            ]
        messages.append({"role": "user", "content": question})

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=[
                {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}
            ],
            messages=messages,
        )
        return resp.content[0].text

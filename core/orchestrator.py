import json
import anthropic
from .agent import Agent
from .kb import KnowledgeBase
from ..memory.session import SessionMemory
from ..memory.store import MemoryStore

# Haiku routes cheaply — decides which agents are actually relevant
_ROUTE_SYSTEM = (
    "You are a routing agent. Given a question and agent descriptions, "
    "return a JSON array of agent names to consult. Pick 1–3 that are genuinely relevant. "
    "Return ONLY the JSON array. Example: [\"strategist\",\"critic\"]"
)

# Sonnet synthesises — sees all perspectives, produces the council decision
_SYNTH_SYSTEM = (
    "You are the Orchestrator of a council of AI advisors. "
    "You receive a question and responses from multiple specialists. "
    "Synthesise their perspectives into a clear, actionable decision. "
    "Name key disagreements. Be concise."
)


class Orchestrator:
    def __init__(
        self,
        agents: dict[str, Agent],
        memory: SessionMemory,
        store: MemoryStore,
        kb: KnowledgeBase,
        mcp_tools: list[dict] | None = None,
    ):
        self.agents = agents
        self.memory = memory
        self.store = store
        self.kb = kb
        self.mcp_tools = mcp_tools or []
        self._router = Agent("router", "claude-haiku-4-5-20251001", _ROUTE_SYSTEM)
        self._synth = Agent("orchestrator", "claude-sonnet-4-6", _SYNTH_SYSTEM)

    # ── routing ────────────────────────────────────────────────────────────────

    def _route(self, question: str) -> list[str]:
        descriptions = "\n".join(
            f"- {name}: {agent.system.splitlines()[0]}"
            for name, agent in self.agents.items()
        )
        raw = self._router.think(f"Question: {question}\n\nAgents:\n{descriptions}")
        try:
            names = json.loads(raw)
            return [n for n in names if n in self.agents] or list(self.agents)[:2]
        except (json.JSONDecodeError, TypeError):
            return list(self.agents)[:2]

    # ── main decision loop ─────────────────────────────────────────────────────

    def decide(self, question: str) -> dict:
        context = self.memory.get_context()
        kb_snippets = self.kb.search(question)
        chosen = self._route(question)

        perspectives: dict[str, str] = {}
        for name in chosen:
            perspectives[name] = self.agents[name].think(question, context, kb_snippets)

        synth_prompt = f"Question: {question}\n\n" + "\n\n".join(
            f"## {name.title()}\n{resp}" for name, resp in perspectives.items()
        )
        decision = self._synth.think(synth_prompt, context)

        self.memory.add(question, perspectives, decision)

        return {
            "question": question,
            "agents_consulted": chosen,
            "perspectives": perspectives,
            "decision": decision,
        }

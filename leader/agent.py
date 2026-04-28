"""
Leader — Agent A.

Responsibilities:
  1. Route: analyse the query and decide which skills to invoke (1-3).
  2. Dispatch: call each chosen skill with shared context.
  3. Judge: receive all responses and deliver the final answer.

The Leader is the only agent the user interacts with.
Sub-agents never speak directly to the user.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Callable

import anthropic

from skills.base import BaseSkill, SkillResponse
from core.models import pick_model, TIERS

if TYPE_CHECKING:
    from core.context import SharedContext
    from memory.session import SessionMemory
    from memory.store import MemoryStore
    from ui.terminal import CouncilUI


_ROUTE_SYSTEM = """\
You are the routing brain of a multi-agent council.
Given a user question and a list of available specialist agents, decide which 1–3 agents are most relevant.
Return ONLY a JSON object — no prose, no markdown:
{"skills": ["name1", "name2"], "reason": "one sentence"}"""

_JUDGE_SYSTEM = """\
You are Agent A — the Leader of this council.
You receive a question and responses from specialist sub-agents you dispatched.
Your job: weigh their perspectives, note disagreements, and deliver ONE clear, final answer.
Do not just summarise — make a decision. Be direct."""


class LeaderAgent:
    def __init__(
        self,
        skills: dict[str, BaseSkill],
        shared_context: "SharedContext",
        memory: "SessionMemory",
        store: "MemoryStore",
        model: str = "claude-sonnet-4-6",
        local_models: list[str] | None = None,
        ui: "CouncilUI | None" = None,
    ) -> None:
        self.skills = skills
        self.shared_context = shared_context
        self.memory = memory
        self.store = store
        self.model = model
        self.local_models = local_models or []
        self.ui = ui
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    # ── routing ───────────────────────────────────────────────────────────────

    def _route(self, question: str, ctx: str) -> list[str]:
        descriptions = "\n".join(
            f"- {name}: {skill.description}"
            for name, skill in self.skills.items()
        )
        routing_model = pick_model("routing", self.local_models)

        # Use local model if available for free routing
        if routing_model.startswith("claude-"):
            resp = self.client.messages.create(
                model=routing_model,
                max_tokens=128,
                system=[{"type": "text", "text": _ROUTE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": f"Question: {question}\n\nAgents:\n{descriptions}"}],
            )
            raw = resp.content[0].text
        else:
            # Ollama routing
            try:
                from openai import OpenAI
                local = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
                r = local.chat.completions.create(
                    model=routing_model,
                    messages=[
                        {"role": "system", "content": _ROUTE_SYSTEM},
                        {"role": "user", "content": f"Question: {question}\n\nAgents:\n{descriptions}"},
                    ],
                )
                raw = r.choices[0].message.content or ""
            except Exception:
                return list(self.skills)[:2]

        try:
            data = json.loads(raw)
            names = data.get("skills", [])
            return [n for n in names if n in self.skills] or list(self.skills)[:2]
        except (json.JSONDecodeError, AttributeError):
            return list(self.skills)[:2]

    # ── judgment ──────────────────────────────────────────────────────────────

    def _judge(self, question: str, perspectives: dict[str, SkillResponse], ctx: str) -> SkillResponse:
        combined = f"Question: {question}\n\n" + "\n\n".join(
            f"## {name.title()}\n{r.text}" for name, r in perspectives.items()
        )
        system_blocks = []
        if ctx:
            system_blocks.append({"type": "text", "text": f"## Shared Context\n{ctx}", "cache_control": {"type": "ephemeral"}})
        system_blocks.append({"type": "text", "text": _JUDGE_SYSTEM, "cache_control": {"type": "ephemeral"}})

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=system_blocks,
            messages=[{"role": "user", "content": combined}],
        )
        u = resp.usage
        return SkillResponse(
            text=resp.content[0].text,
            model=resp.model,
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0),
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0),
        )

    # ── main entry ────────────────────────────────────────────────────────────

    def decide(self, question: str) -> "CouncilResult":
        ctx = self.shared_context.build(
            query=question,
            session_summary=self.memory.get_context(),
        )

        # 1. Route
        if self.ui:
            self.ui.update("leader", "routing")
        chosen = self._route(question, ctx)

        # Mark unchosen skills as skipped in UI
        if self.ui:
            for name in self.skills:
                self.ui.update(name, "skipped" if name not in chosen else "waiting")

        # 2. Dispatch to each chosen skill
        perspectives: dict[str, SkillResponse] = {}
        for name in chosen:
            if self.ui:
                self.ui.update(name, "thinking")
            result = self.skills[name].respond(question, shared_context=ctx)
            perspectives[name] = result
            if self.ui:
                self.ui.update(name, "done", result)

        # 3. Leader judgment
        if self.ui:
            self.ui.update("leader", "judging")
        final = self._judge(question, perspectives, ctx)
        if self.ui:
            self.ui.update("leader", "done", final)

        # 4. Update memory
        self.memory.add(question, {k: v.text for k, v in perspectives.items()}, final.text)

        return CouncilResult(
            question=question,
            skills_consulted=chosen,
            perspectives=perspectives,
            decision=final,
        )


class CouncilResult:
    def __init__(
        self,
        question: str,
        skills_consulted: list[str],
        perspectives: dict[str, SkillResponse],
        decision: SkillResponse,
    ) -> None:
        self.question = question
        self.skills_consulted = skills_consulted
        self.perspectives = perspectives
        self.decision = decision

    @property
    def total_tokens(self) -> int:
        skill_tokens = sum(r.total_tokens for r in self.perspectives.values())
        return skill_tokens + self.decision.total_tokens

    @property
    def total_cached(self) -> int:
        skill_cached = sum(r.cache_read_tokens for r in self.perspectives.values())
        return skill_cached + self.decision.cache_read_tokens

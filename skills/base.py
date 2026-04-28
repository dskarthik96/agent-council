"""
BaseSkill — the interface every Council skill implements.

A skill is a self-contained agent module: one role, one system prompt,
one respond() method. Skills can be used standalone or wired into a Council.

To create a custom skill:
    from skills.base import BaseSkill, SkillResponse

    class MySkill(BaseSkill):
        name = "my-skill"
        description = "What this skill does"
        default_model = "claude-haiku-4-5-20251001"
        system_prompt = "You are..."

        # respond() is inherited — no extra code needed
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import anthropic


@dataclass
class SkillResponse:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_note(self) -> str:
        saved = self.cache_read_tokens
        return f"{self.total_tokens} tok" + (f" ({saved} cached)" if saved else "")


class BaseSkill:
    name: str = "base"
    description: str = ""
    default_model: str = "claude-haiku-4-5-20251001"
    system_prompt: str = "You are a helpful assistant."

    def __init__(
        self,
        model: Optional[str] = None,
        extra_instructions: str = "",
    ) -> None:
        self.model = model or self.default_model
        self.extra_instructions = extra_instructions
        self._client: Optional[anthropic.Anthropic] = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def _build_system(self, shared_context: str = "") -> list[dict]:
        """
        Construct the system message array.

        shared_context is written once and cached across all agent calls in a session —
        every skill reads it from cache rather than paying full input token price.
        """
        blocks: list[dict] = []

        if shared_context:
            blocks.append({
                "type": "text",
                "text": f"## Shared Project Context\n{shared_context}",
                "cache_control": {"type": "ephemeral"},
            })

        role = self.system_prompt
        if self.extra_instructions:
            role += f"\n\n## Additional Instructions\n{self.extra_instructions}"

        blocks.append({
            "type": "text",
            "text": role,
            "cache_control": {"type": "ephemeral"},
        })

        return blocks

    def _is_local(self) -> bool:
        return not self.model.startswith("claude-")

    def respond(
        self,
        question: str,
        shared_context: str = "",
        conversation: Optional[list[dict]] = None,
    ) -> SkillResponse:
        if self._is_local():
            return self._respond_local(question, shared_context, conversation)
        return self._respond_anthropic(question, shared_context, conversation)

    def _respond_anthropic(
        self,
        question: str,
        shared_context: str,
        conversation: Optional[list[dict]],
    ) -> SkillResponse:
        messages = list(conversation or []) + [{"role": "user", "content": question}]
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self._build_system(shared_context),
            messages=messages,
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

    def _respond_local(
        self,
        question: str,
        shared_context: str,
        conversation: Optional[list[dict]],
    ) -> SkillResponse:
        """Call a local Ollama model via its OpenAI-compatible API."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("pip install openai to use local Ollama models")

        local = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

        system = self.system_prompt
        if shared_context:
            system = f"## Shared Project Context\n{shared_context}\n\n{system}"
        if self.extra_instructions:
            system += f"\n\n## Additional Instructions\n{self.extra_instructions}"

        messages = [{"role": "system", "content": system}]
        messages += list(conversation or [])
        messages.append({"role": "user", "content": question})

        resp = local.chat.completions.create(model=self.model, messages=messages)
        text = resp.choices[0].message.content or ""
        usage = resp.usage

        return SkillResponse(
            text=text,
            model=self.model,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
        )

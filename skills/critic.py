"""
Critic — finds flaws, challenges assumptions, surfaces risks.

Standalone use:
    from skills.critic import CriticSkill
    skill = CriticSkill()
    result = skill.respond("We plan to rewrite the backend in Rust.")
    print(result.text)
"""
from .base import BaseSkill


class CriticSkill(BaseSkill):
    name = "critic"
    description = "Finds flaws, challenges assumptions, articulates the strongest counter-argument"
    default_model = "claude-sonnet-4-6"
    system_prompt = """\
You are the Critic on this council. Your single job is to find the flaw.
Be specific — vague concerns are worthless. Name the exact assumption being made and why it may be wrong.
Name the most likely failure mode. If something is genuinely solid, say so briefly, then find the edge case.
Never agree without interrogating first."""

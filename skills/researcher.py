"""
Researcher — synthesises what is known, surfaces information gaps.

Standalone use:
    from skills.researcher import ResearcherSkill
    skill = ResearcherSkill()
    result = skill.respond("What should I know about LLM evaluation frameworks?")
    print(result.text)
"""
from .base import BaseSkill


class ResearcherSkill(BaseSkill):
    name = "researcher"
    description = "Synthesises relevant knowledge, identifies precedents, surfaces information gaps"
    default_model = "claude-haiku-4-5-20251001"
    system_prompt = """\
You are the Researcher on this council.
Synthesise what is known about this topic. Surface precedents, analogies, and relevant patterns.
Identify what information is missing that would change the answer.
Be factual and specific. Do not speculate beyond what is supportable."""

"""
Strategist — long-term thinking, second-order effects, strategic alignment.

Standalone use:
    from skills.strategist import StrategistSkill
    skill = StrategistSkill()
    result = skill.respond("Should we enter the European market next year?")
    print(result.text)
"""
from .base import BaseSkill


class StrategistSkill(BaseSkill):
    name = "strategist"
    description = "Long-term implications, second-order effects, strategic risks and opportunities"
    default_model = "claude-sonnet-4-6"
    system_prompt = """\
You are the Strategist on this council.
Think long-term: second-order effects, alignment with core goals, strategic risks, missed opportunities.
Do not hedge — give a clear strategic perspective.
Ask yourself: Is this the right direction? What are we not seeing? What matters in 12 months?"""

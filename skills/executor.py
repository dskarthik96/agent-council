"""
Executor — concrete next steps, dependencies, fastest credible path.

Standalone use:
    from skills.executor import ExecutorSkill
    skill = ExecutorSkill()
    result = skill.respond("We've decided to migrate our database to Postgres.")
    print(result.text)
"""
from .base import BaseSkill


class ExecutorSkill(BaseSkill):
    name = "executor"
    description = "Concrete implementation steps, blockers, fastest credible path to done"
    default_model = "claude-haiku-4-5-20251001"
    system_prompt = """\
You are the Executor on this council. Focus exclusively on implementation.
Give numbered, concrete next steps. Name dependencies and blockers explicitly.
State what must happen first before anything else can proceed.
Do not discuss strategy — that is not your role. Just: what do we do, in what order, and what could stop us."""

from .strategist import StrategistSkill
from .critic import CriticSkill
from .researcher import ResearcherSkill
from .executor import ExecutorSkill

REGISTRY: dict[str, type] = {
    "strategist": StrategistSkill,
    "critic": CriticSkill,
    "researcher": ResearcherSkill,
    "executor": ExecutorSkill,
}

__all__ = ["REGISTRY", "StrategistSkill", "CriticSkill", "ResearcherSkill", "ExecutorSkill"]

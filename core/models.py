"""
Model registry — knows about cloud and local models, picks the right one per task.
"""
from __future__ import annotations

# Cloud model tiers
TIERS: dict[str, str] = {
    "routing":     "claude-haiku-4-5-20251001",   # cheap routing decisions
    "judgment":    "claude-sonnet-4-6",            # leader final synthesis
    "compression": "claude-haiku-4-5-20251001",   # session memory compression
}


def detect_ollama() -> list[str]:
    """Returns locally available Ollama model names, or [] if Ollama isn't running."""
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


# Prefer fast small local models for cheap tasks
_LOCAL_PREFERRED = ["llama3.2:3b", "llama3.2", "mistral:7b", "mistral", "llama3", "phi3"]


def pick_model(task: str, local_models: list[str], override: str = "") -> str:
    """
    Choose a model for a task.
    - If override is set, use it.
    - For routing/compression: prefer a local model if available (free).
    - Otherwise: use the cloud tier default.
    """
    if override:
        return override

    if task in ("routing", "compression") and local_models:
        for preferred in _LOCAL_PREFERRED:
            if preferred in local_models:
                return preferred
        return local_models[0]

    return TIERS.get(task, TIERS["judgment"])

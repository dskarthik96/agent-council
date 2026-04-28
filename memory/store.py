import json
from datetime import datetime
from pathlib import Path


class MemoryStore:
    """Persistent file-based long-term memory. Each entry is a JSON file."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: dict) -> None:
        data["_saved_at"] = datetime.utcnow().isoformat()
        (self.path / f"{key}.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def load(self, key: str) -> dict | None:
        p = self.path / f"{key}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def all_keys(self) -> list[str]:
        return sorted(p.stem for p in self.path.glob("*.json"))

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        results = []
        for key in self.all_keys():
            data = self.load(key)
            if data and q in json.dumps(data).lower():
                results.append({"key": key, **data})
        return results

    def delete(self, key: str) -> bool:
        p = self.path / f"{key}.json"
        if p.exists():
            p.unlink()
            return True
        return False

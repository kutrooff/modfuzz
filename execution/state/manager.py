from typing import Any, Dict, Optional


class StateManager:
    def __init__(self):
        self.values: Dict[str, Any] = {}

    def save(self, key: str, value: Any):
        self.values[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self.values.get(key)

    def has(self, key, str) -> bool:
        return key in self.values

    def clear(self) -> None:
        self.values.clear()

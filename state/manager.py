from typing import Any, Dict, Optional, List
from state.models import StateValue


class StateManager:
    def __init__(self):
        self.values: Dict[str, Any] = {}

    def save(self,
             key: str,
             value: Any,
             source_path: str,
             source_method: str,
             source_field: str,
    ) -> None:
        self.values[key] = StateValue(
            key=key,
            value=value,
            source_path=source_path,
            source_method=source_method,
            source_field=source_field,
        )

    def get(self, key: str) -> Optional[Any]:
        item = self.values.get(key)
        return item.value if item else None

    def has(self, key: str) -> bool:
        return key in self.values

    def all(self) -> List[StateValue]:
        return list(self.values.values())

    def clear(self) -> None:
        self.values.clear()

from typing import Any, Dict, Optional, List
from state.models import StateValue


class StateManager:
    def __init__(self):
        self.values: Dict[str, StateValue] = {}

    def save(self,
             key: str,
             value: Any,
             source_path: str,
             source_method: str,
             source_field: str,
             json_path: str | None = None,
             resource: str | None = None,
             request_index: int | None = None,
    ) -> None:
        self.values[key] = StateValue(
            key=key,
            value=value,
            source_path=source_path,
            source_method=source_method,
            source_field=source_field,
            resource=resource or self._infer_resource(key),
            value_type=self._infer_value_type(value),
            json_path=json_path,
            request_index=request_index,
        )

    def get(self, key: str) -> Optional[Any]:
        item = self.values.get(key)
        return item.value if item else None

    def has(self, key: str) -> bool:
        return key in self.values

    def all(self) -> List[StateValue]:
        return list(self.values.values())

    def as_dict(self) -> dict[str, Any]:

        return {
            key: state.value
            for key, state in self.values.items()
        }

    def clear(self) -> None:
        self.values.clear()

    def get_state(
            self,
            key: str,
    ) -> Optional[StateValue]:
        return self.values.get(key)

    def _infer_resource(self, key: str) -> str:
        if "." in key:
            return key.split(".", 1)[0]
        return "global"

    def _infer_value_type(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return type(value).__name__

    def metadata(self) -> list[dict[str, Any]]:
        return [
            {
                "key": state.key,
                "value": state.value,
                "resource": state.resource,
                "value_type": state.value_type,
                "json_path": state.json_path,
                "source_path": state.source_path,
                "source_method": state.source_method,
                "source_field": state.source_field,
                "created_at": state.created_at,
                "request_index": state.request_index,
            }
            for state in self.values.values()
        ]

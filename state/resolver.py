from copy import deepcopy
from typing import Any

from schema.models import TestCase
from state.manager import StateManager

class StateResolver:
    """Подставляет значения из StateManager в TestCase"""

    def __init__(self, state_manager: StateManager):
        self.state = state_manager

    def resolve(self, case: TestCase) -> TestCase:
        case = deepcopy(case)

        case.path_params = self._resolve_mapping(case.path_params)
        case.query_params = self._resolve_mapping(case.query_params)
        case.headers = self._resolve_mapping(case.headers)

        if isinstance(case.body, dict):
            case.body = self._resolve_mapping(case.body)

        self._auto_resolve_path_params(case)

        return case

    def _resolve_mapping(self, data: dict | None) -> dict:

        resolved = {}

        for key, value in data.items():
            resolved[key] = self._resolve_value(value)

        return resolved

    def _resolve_value(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith("$state."):
            state_key = value.removeprefix("$state.")
            state_value = self.state.get(state_key)
            return state_value if state_value is not None else value

        if isinstance(value, dict):
            return self._resolve_mapping(value)

        if isinstance(value, list):
            return [self._resolve_value(item) for item in value]

        return value

    def _auto_resolve_path_params(self, case: TestCase) -> None:
        resource_name = self._resource_name_from_path(case.endpoint.path)

        for param_name, current_value in list(case.path_params.items()):
            if current_value not in (None, "", "example"):
                continue

            candidates = [
                f"{resource_name}.{param_name}",
                f"{resource_name}.last_id",
                self._singular(resource_name) + ".last_id",
            ]

            for key in candidates:
                value = self.state.get(key)
                if value is not None:
                    case.path_params[param_name] = value
                    break

    def _resource_name_from_path(self, path: str) -> str:
        parts = [part for part in path.split("/") if part and not part.startswith("{")]
        return parts[0] if parts else "resource"

    def _singular(self, value: str) -> str:
        if value.endswith("ies"):
            return value[:-3] + "y"
        if value.endswith("s"):
            return value[:-1]
        return value



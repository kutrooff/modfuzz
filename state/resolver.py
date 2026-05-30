from copy import deepcopy
from typing import Any

from schema.models import TestCase
from state.manager import StateManager
from state.models import OperationLink

class StateResolver:
    """Подставляет значения из StateManager в TestCase"""

    def __init__(self, state_manager: StateManager):
        self.state = state_manager

    def resolve(self, case: TestCase, links: list[OperationLink] | None = None) -> TestCase:
        case = deepcopy(case)
        self._apply_links(case, links or [])

        case.path_params = self._resolve_mapping(case.path_params)
        case.query_params = self._resolve_mapping(case.query_params)
        case.headers = self._resolve_mapping(case.headers)

        if case.body is not None:
            case.body = self._resolve_value(case.body)

        self._auto_resolve_path_params(case)
        self._inject_auth_header(case)

        unresolved = self._find_unresolved_refs(case)
        if unresolved:
            raise StateResolutionError(unresolved)

        return case

    def _inject_auth_header(self, case: TestCase) -> None:

        if not case.endpoint.requires_auth:
            return

        token = (self.state.get("auth.token") or self.state.get("auth.access_token"))

        if not token:
            return

        if case.headers is None:
            case.headers = {}

        case.headers["Authorization"] = (
            f"Bearer {token}"
        )

    def _resolve_mapping(self, data: dict | None) -> dict:

        if not data:
            return {}

        resolved = {}

        for key, value in data.items():
            resolved[key] = self._resolve_value(value)

        return resolved

    def _resolve_value(self, value: Any) -> Any:

        if isinstance(value, str):

            for state_key, state_value in self.state.as_dict().items():

                placeholder = (
                    f"$state.{state_key}"
                )

                if placeholder in value:
                    value = value.replace(placeholder, str(state_value))

            return value

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
        parts = [
            part for part in path.split("/")
            if part
            and not part.startswith("{")
            and part != "*"
            and not self._is_technical_segment(part)
        ]
        return parts[-1] if parts else "resource"

    def _is_technical_segment(self, value: str) -> bool:
        normalized = (
            value
            .replace("_", "")
            .replace("-", "")
            .lower()
        )

        if normalized in {"api", "rest", "gateway", "service", "services"}:
            return True

        if normalized.startswith("v") and normalized[1:].isdigit():
            return True

        return False

    def _singular(self, value: str) -> str:
        if value.endswith("ies"):
            return value[:-3] + "y"
        if value.endswith("s"):
            return value[:-1]
        return value

    def _apply_links(
            self,
            case: TestCase,
            links: list[OperationLink],
    ) -> None:
        for link in links:
            value = self._resolve_link_value(link)

            if value is None:
                if link.required:
                    raise StateResolutionError(
                        [f"$state.{link.state_key}"]
                    )
                continue

            self._inject_value(case, link.target_location, link.target_param, value)

    def _resolve_link_value(self, link: OperationLink):
        keys = [link.state_key] + link.fallback_state_keys

        for key in keys:
            value = self.state.get(key)
            if value is not None:
                return value

        return None

    def _inject_value(
            self,
            case: TestCase,
            location: str,
            name: str,
            value,
    ) -> None:
        if location == "path":
            case.path_params[name] = value
        elif location == "query":
            case.query_params[name] = value
        elif location == "header":
            case.headers[name] = value
        elif location == "body":
            if case.body is None or not isinstance(case.body, dict):
                case.body = {}
            case.body[name] = value

    def _find_unresolved_refs(self, case: TestCase) -> list[str]:
        refs = []

        refs.extend(self._collect_refs(case.path_params))
        refs.extend(self._collect_refs(case.query_params))
        refs.extend(self._collect_refs(case.headers))
        refs.extend(self._collect_refs(case.body))

        return sorted(set(refs))

    def _collect_refs(self, value: Any) -> list[str]:
        refs = []

        if isinstance(value, str):
            if "$state." in value:
                refs.append(value)
            return refs

        if isinstance(value, dict):
            for item in value.values():
                refs.extend(self._collect_refs(item))
            return refs

        if isinstance(value, list):
            for item in value:
                refs.extend(self._collect_refs(item))
            return refs

        return refs



class StateResolutionError(Exception):
    def __init__(self, unresolved_refs: list[str]):
        self.unresolved_refs = unresolved_refs
        super().__init__(
            f"Unresolved state references: {', '.join(unresolved_refs)}"
        )



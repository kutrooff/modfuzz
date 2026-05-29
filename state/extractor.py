from dataclasses import dataclass
from typing import Any, Dict, List

from execution.result import ExecutionResult
from state.models import OperationLink


@dataclass(frozen=True)
class ExtractedState:
    key: str
    value: Any
    source_field: str
    json_path: str | None = None
    resource: str = ""


class StateExtractor:
    ID_FIELDS = {
        "id",
        "uuid",
        "user_id",
        "userId",
        "order_id",
        "orderId",
    }

    TOKEN_FIELDS = {
        "token",
        "access_token",
        "refresh_token",
    }

    def extract(
            self,
            result: ExecutionResult,
            links: List[OperationLink] | None = None,
    ) -> List[ExtractedState]:
        extracted: Dict[str, ExtractedState] = {}

        if result.status_code is None:
            return []

        self._extract_from_body(result, extracted)
        self._extract_from_headers(result, extracted)

        if links:
            self._extract_from_links(result, links, extracted)

        return list(extracted.values())

    def _extract_from_links(
            self,
            result: ExecutionResult,
            links: List[OperationLink],
            extracted: Dict[str, ExtractedState],
    ) -> None:
        resource_name = self._resource_name_from_path(result.case.endpoint.path)

        for link in links:
            value = self._get_by_json_path(
                result.response_body,
                link.source_json_path,
            )

            if value is None:
                continue

            key = link.state_key or f"{resource_name}.{link.source_field}"

            extracted[key] = ExtractedState(
                key=key,
                value=value,
                source_field=link.source_field,
                json_path=link.source_json_path,
                resource=resource_name,
            )

    def _get_by_json_path(self, data: Any, json_path: str) -> Any:
        if data is None or not json_path.startswith("$"):
            return None

        if json_path == "$":
            return data

        tokens = [
            token
            for token in json_path[1:].lstrip(".").split(".")
            if token
        ]

        values = [data]

        for token in tokens:
            next_values = []
            is_array = token.endswith("[*]")
            key = token[:-3] if is_array else token

            for value in values:
                if key:
                    if not isinstance(value, dict) or key not in value:
                        continue
                    value = value[key]

                if is_array:
                    if isinstance(value, list):
                        next_values.extend(value)
                else:
                    next_values.append(value)

            values = next_values

            if not values:
                return None

        return values[0] if len(values) == 1 else values[0]




    def _extract_from_body(self, result: ExecutionResult, extracted: Dict[str, Any]) -> None:

        body = result.response_body

        resource_name = self._resource_name_from_path(result.case.endpoint.path)

        if isinstance(body, dict):
            self._extract_from_dict(
                body,
                resource_name,
                extracted,
            )

        elif isinstance(body, list):
            for item in body:

                if not isinstance(item, dict):
                    continue

                self._extract_from_dict(
                    item,
                    resource_name,
                    extracted,
                )

    def _extract_from_dict(
            self,
            body: Dict[str, Any],
            resource_name: str,
            extracted: Dict[str, ExtractedState],
            prefix: str = "$",
    ) -> None:
        for field_name, value in body.items():
            json_path = f"{prefix}.{field_name}"

            if field_name in self.ID_FIELDS or field_name.endswith("_id"):
                extracted[f"{resource_name}.{field_name}"] = ExtractedState(
                    key=f"{resource_name}.{field_name}",
                    value=value,
                    source_field=field_name,
                    json_path=json_path,
                    resource=resource_name,
                )

                extracted[f"{resource_name}.last_id"] = ExtractedState(
                    key=f"{resource_name}.last_id",
                    value=value,
                    source_field=field_name,
                    json_path=json_path,
                    resource=resource_name,
                )

            if field_name in self.TOKEN_FIELDS:
                extracted[f"auth.{field_name}"] = ExtractedState(
                    key=f"auth.{field_name}",
                    value=value,
                    source_field=field_name,
                    json_path=json_path,
                    resource="auth",
                )

                extracted["auth.token"] = ExtractedState(
                    key="auth.token",
                    value=value,
                    source_field=field_name,
                    json_path=json_path,
                    resource="auth",
                )

            if isinstance(value, dict):
                self._extract_from_dict(
                    value,
                    resource_name,
                    extracted,
                    json_path,
                )

            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._extract_from_dict(
                            item,
                            resource_name,
                            extracted,
                            f"{json_path}[*]",
                        )

    def _extract_from_headers(
            self,
            result: ExecutionResult,
            extracted: Dict[str, ExtractedState],
    ) -> None:
        headers = {
            key.lower(): value
            for key, value in result.response_headers.items()
        }

        location = headers.get("location")

        if not location:
            return

        extracted["location.last"] = ExtractedState(
            key="location.last",
            value=location,
            source_field="Location",
            json_path=None,
            resource="location",
        )

        last_part = location.rstrip("/").split("/")[-1]

        if not last_part:
            return

        resource_name = self._resource_name_from_path(
            result.case.endpoint.path
        )

        extracted[f"{resource_name}.last_id"] = ExtractedState(
            key=f"{resource_name}.last_id",
            value=last_part,
            source_field="Location",
            json_path=None,
            resource=resource_name,
        )

    def _resource_name_from_path(self, path: str) -> str:
        """
        Возвращает имя ресурса из пути endpoint.
        """

        parts = [
            part
            for part in path.split("/")
            if part and not part.startswith("{")
        ]

        if not parts:
            return "resource"

        return parts[0]
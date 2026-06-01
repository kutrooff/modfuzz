import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class StateLinkOverride:
    source_method: str
    source_path: str
    target_method: str
    target_path: str
    source_json_path: str
    state_key: str
    target_location: str
    target_param: str
    required: bool = True


@dataclass(frozen=True)
class CrossServiceAssertion:
    name: str
    assertion_type: str
    issue: str
    after_method: str | None = None
    after_path: str | None = None
    request_method: str = "GET"
    request_path: str = ""
    bindings: dict[str, Any] | None = None
    query: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    body: Any = None
    expected_statuses: list[int] | None = None
    expected_body: dict[str, Any] | None = None


@dataclass(frozen=True)
class StateConfig:
    links: list[StateLinkOverride] = field(default_factory=list)
    cross_service_assertions: list[CrossServiceAssertion] = field(default_factory=list)


def load_state_config(source: str | None) -> StateConfig:
    if not source:
        return StateConfig(links=[], cross_service_assertions=[])

    path = Path(source)
    text = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".json":
        raw = json.loads(text)
    else:
        raw = yaml.safe_load(text) or {}

    return parse_state_config(raw)


def parse_state_config(raw: dict[str, Any]) -> StateConfig:
    links = []

    for item in raw.get("links", []):
        source_method, source_path = _parse_operation(item["source"])
        target_method, target_path = _parse_operation(item["target"])
        inject = item.get("inject", {})

        links.append(
            StateLinkOverride(
                source_method=source_method,
                source_path=source_path,
                target_method=target_method,
                target_path=target_path,
                source_json_path=item["extract"],
                state_key=item["save_as"],
                target_location=inject["location"],
                target_param=inject["name"],
                required=item.get("required", True),
            )
        )

    return StateConfig(
        links=links,
        cross_service_assertions=_parse_cross_service_assertions(
            raw.get("cross_service_assertions", [])
        ),
    )


def _parse_operation(value: str) -> tuple[str, str]:
    method, path = value.strip().split(maxsplit=1)
    return method.upper(), path


def _parse_cross_service_assertions(raw: Any) -> list[CrossServiceAssertion]:
    if raw is None:
        return []

    if not isinstance(raw, list):
        raise ValueError("cross_service_assertions must be a list")

    assertions = []

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"cross_service_assertions[{index}] must be a mapping")

        request_value = item.get("verify") or item.get("request")
        if not isinstance(request_value, str) or not request_value.strip():
            raise ValueError(
                f"cross_service_assertions[{index}] must define verify or request"
            )

        request_method, request_path = _parse_operation(request_value)

        after_method = None
        after_path = None
        if item.get("after"):
            after_method, after_path = _parse_operation(item["after"])

        expect = item.get("expect", {})
        if expect is None:
            expect = {}
        if not isinstance(expect, dict):
            raise ValueError(f"cross_service_assertions[{index}].expect must be a mapping")

        expected_statuses = _parse_expected_statuses(
            item.get("expect_status", expect.get("status_code"))
        )

        assertion_type = item.get("type") or item.get("issue") or "cross_service_state_mismatch"

        assertions.append(
            CrossServiceAssertion(
                name=item.get("name", f"cross_service_assertion_{index + 1}"),
                assertion_type=assertion_type,
                issue=item.get("issue", assertion_type),
                after_method=after_method,
                after_path=after_path,
                request_method=request_method,
                request_path=request_path,
                bindings=_optional_mapping(item.get("bindings"), "bindings"),
                query=_optional_mapping(item.get("query"), "query"),
                headers=_optional_mapping(item.get("headers"), "headers"),
                body=item.get("body"),
                expected_statuses=expected_statuses,
                expected_body=_optional_mapping(expect.get("body"), "expect.body"),
            )
        )

    return assertions


def _parse_expected_statuses(value: Any) -> list[int]:
    if value is None:
        return []

    if isinstance(value, int) and not isinstance(value, bool):
        return [value]

    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            if not isinstance(item, int) or isinstance(item, bool):
                raise ValueError(f"expect_status[{index}] must be an integer")
            result.append(item)
        return result

    raise ValueError("expect_status must be an integer or a list of integers")


def _optional_mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")

    return value

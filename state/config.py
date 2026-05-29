import json
from dataclasses import dataclass
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
class StateConfig:
    links: list[StateLinkOverride]


def load_state_config(source: str | None) -> StateConfig:
    if not source:
        return StateConfig(links=[])

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

    return StateConfig(links=links)


def _parse_operation(value: str) -> tuple[str, str]:
    method, path = value.strip().split(maxsplit=1)
    return method.upper(), path
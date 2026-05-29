from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import yaml

from generation.mutation_engine import MutationEngine


SUPPORTED_GENERATORS = {
    "example",
    "random",
    "boundary",
}


@dataclass
class MutationLocations:
    body: bool = True
    query: bool = True
    path: bool = False
    headers: bool = False


@dataclass
class StatefulMutationPolicy:
    mutate_setup_requests: bool = False
    mutate_target_requests: bool = True
    mutate_verification_requests: bool = False
    mutate_cleanup_requests: bool = False


@dataclass
class EndpointOverride:
    endpoint: str
    mutations: list[str] = field(default_factory=list)
    locations: MutationLocations | None = None
    mutation_options: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class FuzzingConfig:
    iterations: int = 3
    seed: int | None = None
    generators: list[str] = field(default_factory=lambda: ["example", "random", "boundary"])
    mutations: list[str] = field(default_factory=lambda: ["sql_injection", "xss", "boundary_values"])
    target_methods: list[str] = field(default_factory=list)
    include_paths: list[str] = field(default_factory=list)
    exclude_paths: list[str] = field(default_factory=list)
    locations: MutationLocations = field(default_factory=MutationLocations)
    stateful: StatefulMutationPolicy = field(default_factory=StatefulMutationPolicy)
    mutation_options: dict[str, dict[str, Any]] = field(default_factory=dict)
    overrides: list[EndpointOverride] = field(default_factory=list)


def load_fuzz_config(path: str | None) -> FuzzingConfig:
    if not path:
        return FuzzingConfig()

    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")
    raw = json.loads(text) if config_path.suffix.lower() == ".json" else yaml.safe_load(text)

    return parse_fuzz_config(raw or {})


def parse_fuzz_config(raw: dict[str, Any]) -> FuzzingConfig:
    if not isinstance(raw, dict):
        raise ValueError("Fuzzing config must be a mapping")

    defaults = FuzzingConfig()
    locations = _parse_locations(raw.get("locations"), defaults.locations)
    stateful = _parse_stateful_policy(raw.get("stateful"), defaults.stateful)

    config = FuzzingConfig(
        iterations=_positive_int(raw.get("iterations", defaults.iterations), "iterations"),
        seed=_optional_int(raw.get("seed", defaults.seed), "seed"),
        generators=_parse_string_list(raw.get("generators", defaults.generators), "generators"),
        mutations=_parse_string_list(raw.get("mutations", defaults.mutations), "mutations"),
        target_methods=[
            method.upper()
            for method in _parse_string_list(raw.get("target_methods", defaults.target_methods), "target_methods")
        ],
        include_paths=_parse_string_list(raw.get("include_paths", defaults.include_paths), "include_paths"),
        exclude_paths=_parse_string_list(raw.get("exclude_paths", defaults.exclude_paths), "exclude_paths"),
        locations=locations,
        stateful=stateful,
        mutation_options=_parse_mutation_options(raw.get("mutation_options", {})),
        overrides=_parse_overrides(raw.get("overrides", []), locations),
    )

    mutation_engine = MutationEngine()
    _validate_generators(config.generators)
    mutation_engine.validate_mutations(config.mutations)
    mutation_engine.validate_mutation_options(config.mutation_options)

    for override in config.overrides:
        if override.mutations:
            mutation_engine.validate_mutations(override.mutations)
        mutation_engine.validate_mutation_options(override.mutation_options)

    return config


def _parse_locations(raw: Any, defaults: MutationLocations) -> MutationLocations:
    if raw is None:
        return MutationLocations(
            body=defaults.body,
            query=defaults.query,
            path=defaults.path,
            headers=defaults.headers,
        )

    if not isinstance(raw, dict):
        raise ValueError("locations must be a mapping")

    return MutationLocations(
        body=_bool_value(raw.get("body", defaults.body), "locations.body"),
        query=_bool_value(raw.get("query", defaults.query), "locations.query"),
        path=_bool_value(raw.get("path", defaults.path), "locations.path"),
        headers=_bool_value(raw.get("headers", defaults.headers), "locations.headers"),
    )


def _parse_stateful_policy(raw: Any, defaults: StatefulMutationPolicy) -> StatefulMutationPolicy:
    if raw is None:
        return StatefulMutationPolicy(
            mutate_setup_requests=defaults.mutate_setup_requests,
            mutate_target_requests=defaults.mutate_target_requests,
            mutate_verification_requests=defaults.mutate_verification_requests,
            mutate_cleanup_requests=defaults.mutate_cleanup_requests,
        )

    if not isinstance(raw, dict):
        raise ValueError("stateful must be a mapping")

    return StatefulMutationPolicy(
        mutate_setup_requests=_bool_value(
            raw.get("mutate_setup_requests", defaults.mutate_setup_requests),
            "stateful.mutate_setup_requests",
        ),
        mutate_target_requests=_bool_value(
            raw.get("mutate_target_requests", defaults.mutate_target_requests),
            "stateful.mutate_target_requests",
        ),
        mutate_verification_requests=_bool_value(
            raw.get("mutate_verification_requests", defaults.mutate_verification_requests),
            "stateful.mutate_verification_requests",
        ),
        mutate_cleanup_requests=_bool_value(
            raw.get("mutate_cleanup_requests", defaults.mutate_cleanup_requests),
            "stateful.mutate_cleanup_requests",
        ),
    )


def _parse_overrides(raw: Any, default_locations: MutationLocations) -> list[EndpointOverride]:
    if raw is None:
        return []

    if not isinstance(raw, list):
        raise ValueError("overrides must be a list")

    overrides = []

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"overrides[{index}] must be a mapping")

        endpoint = item.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError(f"overrides[{index}].endpoint must be a non-empty string")

        override_locations = (
            _parse_locations(item["locations"], default_locations)
            if "locations" in item
            else None
        )

        overrides.append(
            EndpointOverride(
                endpoint=_normalize_endpoint(endpoint),
                mutations=_parse_string_list(item.get("mutations", []), f"overrides[{index}].mutations"),
                locations=override_locations,
                mutation_options=_parse_mutation_options(item.get("mutation_options", {})),
            )
        )

    return overrides


def _parse_mutation_options(raw: Any) -> dict[str, dict[str, Any]]:
    if raw is None:
        return {}

    if not isinstance(raw, dict):
        raise ValueError("mutation_options must be a mapping")

    options = {}

    for mutation, value in raw.items():
        if not isinstance(mutation, str) or not mutation.strip():
            raise ValueError("mutation_options keys must be non-empty strings")

        if value is None:
            options[mutation.strip()] = {}
            continue

        if not isinstance(value, dict):
            raise ValueError(f"mutation_options.{mutation} must be a mapping")

        options[mutation.strip()] = value

    return options


def _normalize_endpoint(value: str) -> str:
    parts = value.strip().split(maxsplit=1)

    if len(parts) != 2:
        raise ValueError(f"Endpoint override must look like 'METHOD /path': {value}")

    method, path = parts
    return f"{method.upper()} {path}"


def _parse_string_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")

    result = []

    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{name}[{index}] must be a non-empty string")
        result.append(item.strip())

    return result


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer")

    return value


def _optional_int(value: Any, name: str) -> int | None:
    if value is None:
        return None

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer or null")

    return value


def _bool_value(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be true or false")

    return value


def _validate_generators(generators: list[str]) -> None:
    unknown = set(generators) - SUPPORTED_GENERATORS

    if unknown:
        raise ValueError(
            f"Unknown generators: {', '.join(sorted(unknown))}"
        )

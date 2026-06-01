from copy import deepcopy
import random
from schema.models import TestCase
from generation.config import MutationLocations
from generation.randomized import mutation_engine


def apply_case_mutations(
    case: TestCase,
    fuzz_config,
    iteration: int | None = None,
    mutation_index: int | None = None,
) -> TestCase:
    case = deepcopy(case)

    available_mutations = _mutations_for_case(case, fuzz_config)
    mutations = _select_mutations(
        available_mutations,
        fuzz_config.mutation_policy,
        iteration=iteration,
        mutation_index=mutation_index,
    )
    locations = _locations_for_case(case, fuzz_config)
    mutation_options = _mutation_options_for_case(case, fuzz_config)
    case.applied_mutations = list(mutations)

    if mutations and "mutation" not in case.strategy:
        case.strategy = f"{case.strategy}+mutation"

    if locations.path:
        case.path_params = _mutate_mapping(case.path_params, mutations, mutation_options)

    if locations.query:
        case.query_params = _mutate_mapping(case.query_params, mutations, mutation_options)

    if locations.headers:
        case.headers = _mutate_mapping(case.headers, mutations, mutation_options)

    if locations.body and case.body is not None:
        case.body = mutation_engine.apply_mutations(
            case.body,
            mutations,
            mutation_options,
        )

    return case


def _select_mutations(
    mutations: list[str],
    policy,
    iteration: int | None = None,
    mutation_index: int | None = None,
) -> list[str]:
    if not mutations:
        return []

    mode = getattr(policy, "mode", "all")

    if mode == "all":
        return list(mutations)

    max_per_case = min(
        max(getattr(policy, "max_per_case", 1), 1),
        len(mutations),
    )

    if mode == "one_per_case":
        return list(mutations[:max_per_case])

    if mode == "round_robin":
        start = (mutation_index or 0) % len(mutations)
        return _mutation_window(mutations, start, max_per_case)

    if mode == "per_iteration":
        start = ((iteration or 1) - 1) % len(mutations)
        return _mutation_window(mutations, start, max_per_case)

    if mode == "random_one":
        return random.sample(list(mutations), k=max_per_case)

    return list(mutations)


def _mutation_window(mutations: list[str], start: int, size: int) -> list[str]:
    return [
        mutations[(start + offset) % len(mutations)]
        for offset in range(size)
    ]


def _mutations_for_case(case: TestCase, fuzz_config) -> list[str]:
    override = _override_for_case(case, fuzz_config)

    if override and override.mutations:
        return override.mutations

    return fuzz_config.mutations


def _locations_for_case(case: TestCase, fuzz_config) -> MutationLocations:
    override = _override_for_case(case, fuzz_config)

    if override and override.locations:
        return override.locations

    return fuzz_config.locations


def _mutation_options_for_case(case: TestCase, fuzz_config) -> dict:
    options = {
        mutation: dict(mutation_options)
        for mutation, mutation_options in fuzz_config.mutation_options.items()
    }
    override = _override_for_case(case, fuzz_config)

    if override and override.mutation_options:
        for mutation, mutation_options in override.mutation_options.items():
            merged = dict(options.get(mutation, {}))
            merged.update(mutation_options)
            options[mutation] = merged

    return options


def _mutate_mapping(values: dict, mutations: list[str], mutation_options: dict) -> dict:
    if not values:
        return values

    return {
        key: mutation_engine.apply_mutations(
            value,
            mutations,
            mutation_options,
        )
        for key, value in values.items()
    }


def _override_for_case(case: TestCase, fuzz_config):
    case_endpoint = _case_endpoint_key(case)

    for override in fuzz_config.overrides:
        if override.endpoint == case_endpoint:
            return override

    return None


def _case_endpoint_key(case: TestCase) -> str:
    method = case.method or case.endpoint.method
    return f"{method.upper()} {case.endpoint.path}"

from copy import deepcopy
from schema.models import TestCase
from generation.config import MutationLocations
from generation.randomized import mutation_engine


def apply_case_mutations(case: TestCase, fuzz_config) -> TestCase:
    case = deepcopy(case)

    mutations = _mutations_for_case(case, fuzz_config)
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

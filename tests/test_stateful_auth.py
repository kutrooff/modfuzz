from generation.examples import generate_examples
from schema.loader import load_schema
from schema.parser import parse_openapi
from state.scenario_builder import StatefulScenarioBuilder


def test_stateful_sequences_prepend_auth_for_secured_endpoints():
    endpoints = parse_openapi(load_schema("examples/openapi.yaml"))
    cases = generate_examples(endpoints)

    sequences = StatefulScenarioBuilder().build_sequences(cases)
    secured_sequences = [
        sequence
        for sequence in sequences
        if any(case.endpoint.requires_auth for case in sequence)
    ]

    assert secured_sequences
    assert all(sequence[0].endpoint.path == "/auth/login" for sequence in secured_sequences)
    assert all(sequence[0].role == "setup" for sequence in secured_sequences)
    assert all(sequence[0].body == {"username": "admin", "password": "admin"} for sequence in secured_sequences)

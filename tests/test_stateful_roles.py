from generation.examples import generate_examples
from schema.models import Endpoint, Parameter, RequestBody, Response
from state.models import DependencyGraph, OperationLink
from state.scenario_builder import StatefulScenarioBuilder


def test_lifecycle_sequence_assigns_mutation_roles():
    endpoints = [
        Endpoint(
            path="/users",
            method="POST",
            request_body=RequestBody(schema={"type": "object", "properties": {"name": {"type": "string"}}}),
            responses={201: Response(status_code="201", schema={"type": "object"})},
        ),
        Endpoint(
            path="/users/{userId}",
            method="GET",
            parameters=[Parameter(name="userId", in_="path", type_="string")],
            responses={200: Response(status_code="200")},
        ),
        Endpoint(
            path="/users/{userId}",
            method="PATCH",
            parameters=[Parameter(name="userId", in_="path", type_="string")],
            request_body=RequestBody(schema={"type": "object", "properties": {"name": {"type": "string"}}}),
            responses={200: Response(status_code="200")},
        ),
        Endpoint(
            path="/users/{userId}",
            method="DELETE",
            parameters=[Parameter(name="userId", in_="path", type_="string")],
            responses={204: Response(status_code="204")},
        ),
    ]
    cases = generate_examples(endpoints)
    links = [
        OperationLink(
            source=endpoints[0],
            target=endpoint,
            source_field="id",
            target_param="userId",
            source_json_path="$.id",
            state_key="users.id",
            target_location="path",
        )
        for endpoint in endpoints[1:]
    ]
    graph = DependencyGraph(links=links)
    builder = StatefulScenarioBuilder()

    sequence = builder._build_lifecycle_sequence(cases, graph)

    assert [case.role for case in sequence] == [
        "setup",
        "verification",
        "target",
        "verification",
        "cleanup",
        "verification",
    ]

from generation.case_mutator import apply_case_mutations
from generation.config import parse_fuzz_config
from schema.models import Endpoint, TestCase


def test_apply_case_mutations_uses_endpoint_override():
    endpoint = Endpoint(
        path="/users/{userId}",
        method="PATCH",
    )
    case = TestCase(
        endpoint=endpoint,
        method="PATCH",
        path_params={"userId": "42"},
        query_params={"verbose": "true"},
        body={"name": "Alice"},
    )
    config = parse_fuzz_config(
        {
            "mutations": ["sql_injection"],
            "locations": {
                "body": False,
                "query": True,
                "path": False,
                "headers": False,
            },
            "overrides": [
                {
                    "endpoint": "PATCH /users/{userId}",
                    "mutations": ["large_payload"],
                    "locations": {
                        "body": True,
                        "query": False,
                        "path": False,
                        "headers": False,
                    },
                }
            ],
        }
    )

    mutated = apply_case_mutations(case, config)

    assert mutated.query_params == case.query_params
    assert mutated.path_params == case.path_params
    assert mutated.body["name"] == "Alice" * 1000
    assert case.body["name"] == "Alice"

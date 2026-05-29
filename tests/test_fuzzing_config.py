from generation.config import (
    FuzzingConfig,
    MutationLocations,
    StatefulMutationPolicy,
    parse_fuzz_config,
)


def test_parse_fuzz_config_builds_dataclasses():
    config = parse_fuzz_config(
        {
            "iterations": 7,
            "seed": 42,
            "generators": ["example", "random"],
            "mutations": ["sql_injection", "xss"],
            "target_methods": ["post", "patch"],
            "include_paths": ["/users"],
            "exclude_paths": ["/health"],
            "locations": {
                "body": True,
                "query": False,
                "path": False,
                "headers": True,
            },
            "stateful": {
                "mutate_setup_requests": False,
                "mutate_target_requests": True,
                "mutate_verification_requests": False,
                "mutate_cleanup_requests": False,
            },
            "overrides": [
                {
                    "endpoint": "patch /users/{userId}",
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

    assert isinstance(config, FuzzingConfig)
    assert isinstance(config.locations, MutationLocations)
    assert isinstance(config.stateful, StatefulMutationPolicy)
    assert config.iterations == 7
    assert config.seed == 42
    assert config.target_methods == ["POST", "PATCH"]
    assert config.overrides[0].endpoint == "PATCH /users/{userId}"
    assert config.overrides[0].locations.body is True


def test_parse_fuzz_config_rejects_unknown_mutation():
    try:
        parse_fuzz_config({"mutations": ["does_not_exist"]})
    except ValueError as exc:
        assert "Unknown mutations" in str(exc)
    else:
        raise AssertionError("unknown mutation was accepted")


def test_parse_fuzz_config_rejects_unknown_generator():
    try:
        parse_fuzz_config({"generators": ["example", "strange"]})
    except ValueError as exc:
        assert "Unknown generators" in str(exc)
    else:
        raise AssertionError("unknown generator was accepted")

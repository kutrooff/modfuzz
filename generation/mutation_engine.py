from copy import deepcopy
from random import choice, randint, random
from string import ascii_letters


class MutationEngine:


    SUPPORTED_MUTATIONS = {
        "sql_injection",
        "xss",
        "large_payload",
        "random",
        "type_confusion",
        "negative_numbers",
        "boundary_values",
        "invalid_types",
        "deep_json",
    }

    SQL_PAYLOADS = [
        "' OR 1=1 --",
        "'; DROP TABLE users; --",
        "\" OR \"1\"=\"1",
    ]

    XSS_PAYLOADS = [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>",
    ]

    BOUNDARY_NUMBERS = [
        -1,
        0,
        1,
        2**31 - 1,
        -(2**31),
        999999999,
    ]

    INVALID_TYPES = [
        [],
        {},
        None,
        True,
        False,
        "invalid",
        999999,
    ]

    def apply_mutations(self, data, mutations: list[str]):

        self.validate_mutations(mutations)

        mutated = deepcopy(data)

        for mutation in mutations:
            mutated = self._mutate(mutated, mutation)

        return mutated

    def _mutate(self, value, mutation):

        if isinstance(value, dict):
            return self._mutate_object(value, mutation)

        if isinstance(value, list):
            return self._mutate_array(value, mutation)

        if isinstance(value, str):
            return self._mutate_string(value, mutation)

        if isinstance(value, bool):
            return self._mutate_boolean(value, mutation)

        if isinstance(value, int):
            return self._mutate_integer(value, mutation)

        return value

    def _mutate_object(self, obj: dict, mutation):

        mutated = {}

        for key, value in obj.items():
            mutated[key] = self._mutate(value, mutation)

        if mutation == "deep_json":
            current = mutated

            for i in range(20):
                current["nested"] = {}
                current = current["nested"]

        if mutation == "type_confusion":
            mutated["unexpected_object"] = [
                {"a": {"b": {"c": "boom"}}}
            ]

        return mutated

    def _mutate_array(self, arr: list, mutation):

        mutated = [
            self._mutate(item, mutation)
            for item in arr
        ]

        if mutation == "large_payload":
            mutated *= 100

        return mutated

    def _mutate_string(self, value: str, mutation):

        if mutation == "sql_injection":
            return choice(self.SQL_PAYLOADS)

        if mutation == "xss":
            return choice(self.XSS_PAYLOADS)

        if mutation == "large_payload":
            return value * 1000

        if mutation == "random":
            return "".join(
                choice(ascii_letters)
                for _ in range(randint(100, 500))
            )

        if mutation == "type_confusion":
            return {
                "confused": True
            }

        return value

    def _mutate_integer(self, value: int, mutation):

        if mutation == "negative_numbers":
            return -abs(value)

        if mutation == "boundary_values":
            return choice(self.BOUNDARY_NUMBERS)

        if mutation == "invalid_types":
            return "not_an_integer"

        if mutation == "large_payload":
            return 10**10

        return value

    def _mutate_boolean(self, value: bool, mutation):

        if mutation == "invalid_types":
            return "true"

        return not value

    def validate_mutations(self, mutations: list[str]) -> None:
        unknown = set(mutations) - self.SUPPORTED_MUTATIONS

        if unknown:
            raise ValueError(
                f"Unknown mutations: {', '.join(sorted(unknown))}"
            )

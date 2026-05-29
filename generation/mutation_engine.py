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

    def apply_mutations(self, data, mutations: list[str], options: dict | None = None):

        self.validate_mutations(mutations)
        self.validate_mutation_options(options or {})

        mutated = deepcopy(data)

        for mutation in mutations:
            mutated = self._mutate(mutated, mutation, options or {})

        return mutated

    def _mutate(self, value, mutation, options):

        if isinstance(value, dict):
            return self._mutate_object(value, mutation, options)

        if isinstance(value, list):
            return self._mutate_array(value, mutation, options)

        if isinstance(value, str):
            return self._mutate_string(value, mutation, options)

        if isinstance(value, bool):
            return self._mutate_boolean(value, mutation, options)

        if isinstance(value, int):
            return self._mutate_integer(value, mutation, options)

        return value

    def _mutate_object(self, obj: dict, mutation, options):
        mutation_options = self._options_for(options, mutation)

        mutated = {}

        for key, value in obj.items():
            mutated[key] = self._mutate(value, mutation, options)

        if mutation == "deep_json":
            current = mutated

            for i in range(self._int_option(mutation_options, "depth", 20, minimum=1)):
                current["nested"] = {}
                current = current["nested"]

        if mutation == "type_confusion":
            mutated["unexpected_object"] = [
                {"a": {"b": {"c": "boom"}}}
            ]

        return mutated

    def _mutate_array(self, arr: list, mutation, options):
        mutation_options = self._options_for(options, mutation)

        mutated = [
            self._mutate(item, mutation, options)
            for item in arr
        ]

        if mutation == "large_payload":
            mutated *= self._int_option(mutation_options, "array_repeat", 100, minimum=1)

        return mutated

    def _mutate_string(self, value: str, mutation, options):
        mutation_options = self._options_for(options, mutation)

        if mutation == "sql_injection":
            return choice(self._list_option(mutation_options, "payloads", self.SQL_PAYLOADS))

        if mutation == "xss":
            return choice(self._list_option(mutation_options, "payloads", self.XSS_PAYLOADS))

        if mutation == "large_payload":
            return value * self._int_option(mutation_options, "string_repeat", 1000, minimum=1)

        if mutation == "random":
            min_length = self._int_option(mutation_options, "min_length", 100, minimum=0)
            max_length = self._int_option(mutation_options, "max_length", 500, minimum=min_length)
            return "".join(
                choice(ascii_letters)
                for _ in range(randint(min_length, max_length))
            )

        if mutation == "type_confusion":
            return {
                "confused": True
            }

        return value

    def _mutate_integer(self, value: int, mutation, options):
        mutation_options = self._options_for(options, mutation)

        if mutation == "negative_numbers":
            return -abs(value)

        if mutation == "boundary_values":
            return choice(self._list_option(mutation_options, "numbers", self.BOUNDARY_NUMBERS))

        if mutation == "invalid_types":
            return choice(self._list_option(mutation_options, "values", ["not_an_integer"]))

        if mutation == "large_payload":
            return self._int_option(mutation_options, "integer_value", 10**10)

        return value

    def _mutate_boolean(self, value: bool, mutation, options):
        mutation_options = self._options_for(options, mutation)

        if mutation == "invalid_types":
            return choice(self._list_option(mutation_options, "values", ["true"]))

        return not value

    def validate_mutations(self, mutations: list[str]) -> None:
        unknown = set(mutations) - self.SUPPORTED_MUTATIONS

        if unknown:
            raise ValueError(
                f"Unknown mutations: {', '.join(sorted(unknown))}"
            )

    def validate_mutation_options(self, options: dict[str, dict]) -> None:
        unknown = set(options) - self.SUPPORTED_MUTATIONS

        if unknown:
            raise ValueError(
                f"Unknown mutation options: {', '.join(sorted(unknown))}"
            )

    def _options_for(self, options: dict, mutation: str) -> dict:
        value = options.get(mutation, {})
        return value if isinstance(value, dict) else {}

    def _int_option(self, options: dict, name: str, default: int, minimum: int | None = None) -> int:
        value = options.get(name, default)

        if not isinstance(value, int) or isinstance(value, bool):
            return default

        if minimum is not None and value < minimum:
            return default

        return value

    def _list_option(self, options: dict, name: str, default: list):
        value = options.get(name, default)

        if not isinstance(value, list) or not value:
            return default

        return value

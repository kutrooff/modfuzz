from random import choices, randint, choice
from string import ascii_letters, digits
from typing import List, Any
from schema.models import Endpoint, TestCase
from generation.mutation_engine import MutationEngine

mutation_engine = MutationEngine()

def random_string(length: int=10) -> str:
    """
    Генерирует случайную строку заданной длины:
    :param length длина строки
    :return:
        str Случайно сформированная строка из букв и цифр
    """
    return "".join(choices(ascii_letters + digits, k=length))

def random_value(param_type: str) -> Any:
    """
    Генерирует случайное значение определенного типа:
    :param param_type тип для генерации
    """
    if param_type == "string":

        dangerous_values = [
            "error",
            "crash",
            "slow",
            "empty",
            "invalid",
            "random",

            "' OR 1=1 --",
            "<script>alert(1)</script>",
            "../../../etc/passwd",
            "A" * 10000,
            "",
        ]

        if randint(1, 4) == 1:
            return choice(dangerous_values)

        return random_string(randint(0, 50))

    elif param_type == "integer":
        return randint(-1000, 1000)
    elif param_type == "boolean":
        return choice([True, False])
    elif param_type == "array":
        return [random_string(5) for _ in range(randint(0,5))]
    else:
        return "example"

def generate_from_schema(schema: dict):
    """
    Генерирует request body на основе OpenAPI schema.
    """

    schema_type = schema.get("type")

    if schema_type == "string":
        return schema.get("example", random_string(randint(5, 15)))

    elif schema_type == "integer":
        return schema.get("example", randint(0, 1000))

    elif schema_type == "boolean":
        return choice([True, False])

    elif schema_type == "array":
        items_schema = schema.get("items", {})
        return [generate_from_schema(items_schema)]

    elif schema_type == "object":
        result = {}

        properties = schema.get("properties", {})

        for property_name, property_schema in properties.items():
            result[property_name] = generate_from_schema(property_schema)

        return result

    return None

def generate_random_cases(endpoints: List[Endpoint], n: int = 3, mutations=None) -> List[TestCase]:
    test_cases = []

    for endpoint in endpoints:
        for _ in range(n):
            path_params = {p.name: random_value(p.type_) for p in endpoint.parameters if p.in_ == "path"}
            query_params = {p.name: random_value(p.type_) for p in endpoint.parameters if p.in_ == "query"}
            headers = {
                p.name: random_value(p.type_)
                for p in endpoint.parameters
                if p.in_ == "header"
            }
            if endpoint.requires_auth:
                headers["Authorization"] = "Bearer $state.auth.token"

            body = (
                generate_from_schema(endpoint.request_body.schema)
                if endpoint.request_body
                else None
            )

            if body and mutations:
                body = mutation_engine.apply_mutations(
                    body,
                    mutations,
                )

            test_cases.append(
                TestCase(
                    endpoint=endpoint,
                    method=endpoint.method,
                    path_params=path_params,
                    query_params=query_params,
                    headers=headers,
                    body=body,
                    expected_statuses=list(endpoint.responses.keys()) if endpoint.responses else [200],
                    strategy="random"
                )
            )

    return test_cases
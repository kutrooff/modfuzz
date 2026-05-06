from typing import List

from schema.models import Endpoint, TestCase


def generate_boundary_cases(endpoints: List[Endpoint]) -> List[TestCase]:
    """Генерирует тестовые случаи с граничными значениями:
    :param endpoints список заданных эндпоинтов
    :return:
        List[TestCase] список тест-кейсов
    """
    test_cases: List[TestCase] = []

    for endpoint in endpoints:
        for param in endpoint.parameters:
            boundary_values = []

            if param.type_ == "interger":
                minimum = param.schema.get("minimum", 0)
                maximum = param.schema.get("maximum", 100)
                boundary_values = [minimum, maximum, minimum - 1, maximum + 1]

            elif param.type_ == "string":
                min_length = param.schema.get("minLength", 0)
                max_length = param.schema.get("maxLength", 10)
                boundary_values = ["", "a" * min_length, "a" * max_length, "a" * (max_length + 1)]

            else:
                boundary_values = [param.example or "example"]

            for value in boundary_values:
                path_params = {}
                query_params = {}
                headers = {}

                if param.in_ == "path":
                    path_params[param.name] = value
                elif param.in_ == "query":
                    query_params[param.name] = value
                elif param.in_ == "header":
                    headers[param.name] = value

                body = None
                if endpoint.request_body:
                    # Для body используем пример, если есть
                    body = endpoint.request_body.schema.get("example", {"example_field": "example"})

                expected_statuses = list(endpoint.responses.keys()) if endpoint.responses else [200]

                test_cases.append(
                    TestCase(
                        endpoint=endpoint,
                        method=endpoint.method,
                        path_params=path_params,
                        query_params=query_params,
                        headers=headers,
                        body=body,
                        expected_statuses=expected_statuses,
                        strategy="boundary"
                    )
                )

    return test_cases
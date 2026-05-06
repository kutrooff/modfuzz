from typing import List

from schema.models import Endpoint, TestCase

def generate_examples(endpoints: List[Endpoint]) -> List[TestCase]:
    """
    Генерирует тестовые случаи (TestCase) из примеров, указанных в OpenAPI
    :param endpoints список заданных эндпоинтов
    :return
        List[TestCase] список тест-кейсов
    """
    test_cases: List[TestCase] = []

    for endpoint in endpoints:
        path_params = {}
        query_params = {}
        headers = {}

        for param in endpoint.parameters:
            example_value = param.example if param.example is not None else "example"
            if param.in_ == "path":
                path_params[param.name] = example_value
            elif param.in_ == "query":
                query_params[param.name] = example_value
            elif param.in_ == "header":
                headers[param.name] = example_value

        body = None
        if endpoint.request_body:
            body = endpoint.request_body.schema.get("example", {"example_field": "example"})

        expected_statuses = list(endpoint.responses.keys()) if endpoint.responses else [200]

        test_case = TestCase(
            endpoint=endpoint,
            method=endpoint.method,
            path_params=path_params,
            query_params=query_params,
            headers=headers,
            body=body,
            expected_statuses=expected_statuses,
            strategy="example"
        )
        test_cases.append(test_case)

    return test_cases
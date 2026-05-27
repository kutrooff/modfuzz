from typing import List

from schema.models import Endpoint, TestCase

LOGIN_EXAMPLES = {
    "username": "admin",
    "password": "admin"
}

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

        if endpoint.requires_auth:

            headers["Authorization"] = (
                "Bearer $state.auth.token"
            )

        body = None

        if endpoint.path == "/login":
            body = LOGIN_EXAMPLES

        if endpoint.request_body:
            schema = endpoint.request_body.schema



            if schema.get("type") == "object":
                body = {}

                properties = schema.get("properties", {})

                for property_name, property_schema in properties.items():
                    if "example" in property_schema:
                        body[property_name] = property_schema["example"]
                    else:
                        property_type = property_schema.get("type")

                        if property_type == "string":
                            body[property_name] = "example"

                        elif property_type == "integer":
                            body[property_name] = 1

                        elif property_type == "boolean":
                            body[property_name] = True

                        else:
                            body[property_name] = None
            else:
                body = schema.get("example")

        expected_statuses = (
            [int(code) for code in endpoint.responses.keys()]
            if endpoint.responses
            else [200]
        )

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
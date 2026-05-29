from typing import List, Dict
from schema.models import Endpoint, Parameter, RequestBody, Response

def parse_openapi(schema: Dict) -> List[Endpoint]:

    valid_methods = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "options",
        "head",
    }

    endpoints: List[Endpoint] = []

    paths = schema.get("paths", {})
    for path, methods in paths.items():
        for method, info in methods.items():
            if method.lower() not in valid_methods:
                continue

            all_parameters = (methods.get("parameters", []) + info.get("parameters", []))

            parameters = _parse_parameters(all_parameters)

            request_body = _parse_request_body(info, schema)

            responses = _parse_responses(info, schema)

            # Создание Endpoint
            endpoint = Endpoint(
                path=path,
                method=method.upper(),
                summary=info.get("summary", ""),
                description=info.get("description", ""),
                parameters=parameters,
                request_body=request_body,
                responses=responses,
                tags=info.get("tags", []),
                requires_auth=_requires_auth(info)
            )
            endpoints.append(endpoint)

    return endpoints

def _parse_parameters(all_parameters: List[Dict]):
    parameters = []
    for param in all_parameters:
        parameters.append(
            Parameter(
                name=param.get("name"),
                in_=param.get("in"),
                type_=param.get("schema", {}).get("type", "string"),
                required=param.get("required", False),
                schema=param.get("schema", {}),
                example=param.get("example"),
            )
        )

    return parameters

def _parse_request_body(info: dict, schema: dict):
    request_body = None
    if "requestBody" in info:
        content = info["requestBody"].get("content", {})
        if "application/json" in content:
            raw_schema = content["application/json"].get("schema", {})

            if "$ref" in raw_schema:
                schema_body = resolve_ref(raw_schema["$ref"], schema)
            else:
                schema_body = raw_schema

            request_body = RequestBody(
                content_type="application/json",
                schema=schema_body,
                required=info["requestBody"].get("required", True),
            )

    return request_body

def _parse_responses(info: dict, schema: dict):
    responses = {}

    for status, resp in info.get("responses", {}).items():
        raw_schema = (
            resp.get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )

        if "$ref" in raw_schema:
            response_schema = resolve_ref(raw_schema["$ref"], schema)
        else:
            response_schema = raw_schema

        responses[status] = Response(
            status_code=status,
            description=resp.get("description", ""),
            schema=response_schema,
            content_type="application/json",
        )

    return responses

def resolve_ref(ref: str, schema: dict):
    path = ref.replace("#/", "").split("/")

    current = schema

    try:
        for part in path:
            current = current[part]

    except KeyError:
        raise ValueError(f"Invalid OpenAPI reference: {ref}")

    return current

def _requires_auth(info: dict) -> bool:
    return bool(info.get("security"))
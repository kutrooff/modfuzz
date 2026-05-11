from typing import List, Dict
from schema.models import Endpoint, Parameter, RequestBody, Response

def parse_openapi(schema: Dict) -> List[Endpoint]:
    endpoints: List[Endpoint] = []

    paths = schema.get("paths", {})
    for path, methods in paths.items():
        for method, info in methods.items():
            # Параметры
            parameters = []
            for param in info.get("parameters", []):
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
            # RequestBody
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
            # Responses
            responses = {}
            for status, resp in info.get("responses", {}).items():
                responses[int(status)] = Response(
                    status_code=int(status),
                    description=resp.get("description", ""),
                    schema=resp.get("content", {}).get("application/json", {}).get("schema", {}),
                    content_type="application/json"
                )
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
            )
            endpoints.append(endpoint)
    return endpoints

def resolve_ref(ref: str, schema: dict):
    path = ref.replace("#/", "").split("/")

    current = schema

    for part in path:
        current = current[part]

    return current
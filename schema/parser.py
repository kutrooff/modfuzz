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

            parameters = _parse_parameters(all_parameters, schema)

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
                operation_id=info.get("operationId", ""),
                requires_auth=_requires_auth(info)
            )
            endpoints.append(endpoint)

    return endpoints

def _parse_parameters(all_parameters: List[Dict], schema: dict):
    parameters = []
    for param in all_parameters:
        if "$ref" in param:
            param = resolve_ref(param["$ref"], schema)

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

            schema_body = resolve_schema(raw_schema, schema)

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

        response_schema = resolve_schema(raw_schema, schema)

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

def resolve_schema(schema_fragment, schema: dict, seen: set[str] | None = None):
    seen = seen or set()

    if isinstance(schema_fragment, list):
        return [
            resolve_schema(item, schema, seen)
            for item in schema_fragment
        ]

    if not isinstance(schema_fragment, dict):
        return schema_fragment

    if "$ref" in schema_fragment:
        ref = schema_fragment["$ref"]

        if ref in seen:
            return {}

        resolved = resolve_schema(
            resolve_ref(ref, schema),
            schema,
            seen | {ref},
        )
        siblings = {
            key: value
            for key, value in schema_fragment.items()
            if key != "$ref"
        }

        if not siblings:
            return resolved

        return _merge_schema_dicts(
            resolved if isinstance(resolved, dict) else {},
            resolve_schema(siblings, schema, seen),
        )

    resolved = {
        key: resolve_schema(value, schema, seen)
        for key, value in schema_fragment.items()
    }

    if "allOf" in resolved:
        merged = {}

        for item in resolved.get("allOf", []):
            if isinstance(item, dict):
                merged = _merge_schema_dicts(merged, item)

        extra = {
            key: value
            for key, value in resolved.items()
            if key != "allOf"
        }

        return _merge_schema_dicts(merged, extra)

    return resolved

def _merge_schema_dicts(base: dict, extra: dict) -> dict:
    merged = dict(base)

    if "properties" in base or "properties" in extra:
        merged["properties"] = {
            **base.get("properties", {}),
            **extra.get("properties", {}),
        }

    if "required" in base or "required" in extra:
        merged["required"] = list(
            dict.fromkeys(
                list(base.get("required", []))
                + list(extra.get("required", []))
            )
        )

    for key, value in extra.items():
        if key in {"properties", "required"}:
            continue
        merged[key] = value

    if "type" not in merged and "properties" in merged:
        merged["type"] = "object"

    return merged

def _requires_auth(info: dict) -> bool:
    return bool(info.get("security"))

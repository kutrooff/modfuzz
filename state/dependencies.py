from typing import List
from dataclasses import dataclass
import re

from schema.models import Endpoint
from state.models import DependencyGraph, OperationLink
from state.config import StateConfig, StateLinkOverride


@dataclass(frozen=True)
class ResponseField:
    name: str
    json_path: str
    type_: str | None = None


class DependencyAnalyzer:
    """
    Строит простые зависимости между endpoint-ами.

    Первая версия:
    - producer: POST /resources с ответом, где есть id;
    - consumer: GET/PUT/PATCH/DELETE /resources/{id};
    - связь строится по совпадению первого сегмента пути.
    """

    def __init__(self, config: StateConfig | None = None):
        self.config = config or StateConfig(links=[])

    MIN_CONFIDENCE = 0.55
    PRODUCER_METHODS = {"POST"}
    CONSUMER_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    TECHNICAL_SEGMENTS = {
        "api",
        "rest",
        "gateway",
        "service",
        "services",
    }

    def analyze(self, endpoints: List[Endpoint]) -> DependencyGraph:
        graph = DependencyGraph()

        producers = [
            endpoint for endpoint in endpoints
            if self._is_producer(endpoint)
        ]

        consumers = [
            endpoint for endpoint in endpoints
            if self._is_consumer(endpoint)
        ]

        for producer in producers:
            produced_fields = self._extract_response_fields(producer)

            for consumer in consumers:
                path_params = [
                    param for param in consumer.parameters
                    if param.in_ in {"path", "query"}
                ]

                for param in path_params:
                    link = self._build_best_link(
                        producer=producer,
                        consumer=consumer,
                        target_param=param,
                        produced_fields=produced_fields,
                    )

                    if link:
                        graph.links.append(link)

        graph.links = self._select_best_links(graph.links)
        self._apply_config_overrides(graph, endpoints)
        return graph

    def _select_best_links(self, links: List[OperationLink]) -> List[OperationLink]:
        best: dict[tuple[str, str, str, str, str], OperationLink] = {}

        for link in links:
            key = (
                link.target.method,
                link.target.path,
                link.target_location,
                link.target_param,
                link.source_json_path,
            )
            current = best.get(key)

            if current is None or link.confidence > current.confidence:
                best[key] = link

        by_target_param: dict[tuple[str, str, str, str], OperationLink] = {}

        for link in best.values():
            key = (
                link.target.method,
                link.target.path,
                link.target_location,
                link.target_param,
            )
            current = by_target_param.get(key)

            if current is None or link.confidence > current.confidence:
                by_target_param[key] = link

        return list(by_target_param.values())

    def _is_producer(self, endpoint: Endpoint) -> bool:
        if endpoint.method.upper() not in self.PRODUCER_METHODS:
            return False

        return self._has_success_response(endpoint)

    def _is_consumer(self, endpoint: Endpoint) -> bool:
        if endpoint.method.upper() not in self.CONSUMER_METHODS:

            return False
        return any(param.in_ in {"path", "query"} for param in endpoint.parameters)

    def _resource_name(self, path: str) -> str:
        parts = self._resource_segments(path)

        return parts[-1] if parts else "resource"

    def _resource_segments(self, path: str) -> list[str]:
        result = []

        for part in path.split("/"):
            if not part or part.startswith("{") or part == "*":
                continue

            normalized = self._normalize_name(part)

            if self._is_technical_segment(normalized):
                continue

            result.append(part)

        return result

    def _is_technical_segment(self, normalized: str) -> bool:
        if normalized in self.TECHNICAL_SEGMENTS:
            return True

        if re.fullmatch(r"v\d+", normalized):
            return True

        if re.fullmatch(r"api\d*", normalized):
            return True

        return False

    def _has_success_response(self,endpoint: Endpoint,) -> bool:

        for status in endpoint.responses.keys():

            if not str(status).isdigit():
                continue

            if 200 <= int(status) < 300:
                return True

        return False

    def _extract_response_fields(self, endpoint: Endpoint) -> List[ResponseField]:
        fields: List[ResponseField] = []

        for response in endpoint.responses.values():
            fields.extend(
                self._flatten_schema_fields(
                    response.schema,
                    prefix="$",
                )
            )

        return fields

    def _flatten_schema_fields(
            self,
            schema: dict,
            prefix: str = "$",
    ) -> List[ResponseField]:
        fields: List[ResponseField] = []

        if not schema:
            return fields

        if "allOf" in schema:
            for item in schema.get("allOf", []):
                fields.extend(
                    self._flatten_schema_fields(
                        item,
                        prefix,
                    )
                )

        if "oneOf" in schema or "anyOf" in schema:
            for item in schema.get("oneOf", []) + schema.get("anyOf", []):
                fields.extend(
                    self._flatten_schema_fields(
                        item,
                        prefix,
                    )
                )

        schema_type = schema.get("type")

        if schema_type == "object" or "properties" in schema:
            properties = schema.get("properties", {})

            for field_name, field_schema in properties.items():
                json_path = f"{prefix}.{field_name}"

                fields.append(
                    ResponseField(
                        name=field_name,
                        json_path=json_path,
                        type_=field_schema.get("type"),
                    )
                )

                fields.extend(
                    self._flatten_schema_fields(
                        field_schema,
                        json_path,
                    )
                )

        elif schema_type == "array":
            fields.extend(
                self._flatten_schema_fields(
                    schema.get("items", {}),
                    f"{prefix}[*]",
                )
            )

        return fields

    def _normalize_name(self, value: str) -> str:
        return (
            value
            .replace("_", "")
            .replace("-", "")
            .replace(".", "")
            .lower()
        )

    def _score_candidate(self, producer, consumer, target_param, field: ResponseField):
        score = 0.0
        reasons = []

        producer_resource = self._resource_name(producer.path)
        consumer_resource = self._resource_name(consumer.path)
        target_resource = self._resource_from_param(
            consumer.path,
            target_param.name,
        )

        producer_matches_target = (
            target_resource
            and self._resource_matches(producer_resource, target_resource)
        )

        if producer_resource == consumer_resource:
            score += 0.20
            reasons.append("same_resource")

        if producer_matches_target:
            score += 0.35
            reasons.append("producer_matches_target_param_resource")

        elif producer_resource != consumer_resource:
            score -= 0.15
            reasons.append("different_resource")

        target_name = target_param.name
        target_norm = self._normalize_name(target_name)
        field_norm = self._normalize_name(field.name)
        field_context = self._normalize_name(field.json_path)

        if target_name == field.name:
            score += 0.45
            reasons.append("exact_name_match")

        elif target_norm == field_norm:
            score += 0.40
            reasons.append("normalized_name_match")

        if target_norm.endswith("id") and field_norm == "id" and producer_matches_target:
            score += 0.35
            reasons.append("producer_id_matches_target_id")

        elif target_norm.endswith("id") and field_norm == "id":
            score -= 0.30
            reasons.append("producer_id_does_not_match_target_resource")

        if (
                target_param.in_ == "path"
                and target_norm == field_norm
                and not producer_matches_target
        ):
            score -= 0.25
            reasons.append("foreign_key_not_preferred_for_path_param")

        if target_resource and field_norm == "id" and producer_matches_target:
            score += 0.10
            reasons.append("resource_id_match")

        if target_resource and self._normalize_name(target_resource) in field_context:
            score += 0.10
            reasons.append("resource_name_in_response_path")

        if self._endpoint_metadata_matches(producer, target_resource):
            score += 0.10
            reasons.append("producer_metadata_match")

        if self._endpoint_metadata_matches(consumer, target_resource):
            score += 0.05
            reasons.append("consumer_metadata_match")

        if field_norm == "uuid":
            score += 0.15
            reasons.append("uuid_fallback")

        if field.json_path.startswith("$.data.") or field.json_path.startswith("$.result."):
            score += 0.10
            reasons.append("common_wrapper_path")

        return score, ", ".join(reasons)

    def _resource_from_param(self, path: str, param_name: str) -> str | None:
        param_norm = self._normalize_name(param_name)

        for suffix in ("id", "uuid", "key"):
            if param_norm.endswith(suffix) and len(param_norm) > len(suffix):
                return param_norm[:-len(suffix)]

        segments = [
            part for part in path.split("/")
            if part and not part.startswith("{") and part != "*"
        ]
        marker = "{" + param_name + "}"

        for index, part in enumerate(path.split("/")):
            if part == marker:
                previous = [
                    segment for segment in path.split("/")[:index]
                    if segment and not segment.startswith("{") and segment != "*"
                ]
                return previous[-1] if previous else None

        return segments[-1] if segments else None

    def _resource_matches(self, left: str, right: str) -> bool:
        left_norm = self._singular(self._normalize_name(left))
        right_norm = self._singular(self._normalize_name(right))
        return left_norm == right_norm

    def _path_contains_resource(self, path: str, resource: str) -> bool:
        return any(
            self._resource_matches(segment, resource)
            for segment in self._resource_segments(path)
        )

    def _endpoint_metadata_matches(self, endpoint: Endpoint, resource: str | None) -> bool:
        if not resource:
            return False

        resource_norm = self._singular(self._normalize_name(resource))
        values = [endpoint.operation_id, endpoint.summary, endpoint.description]
        values.extend(endpoint.tags or [])

        return any(
            resource_norm in self._singular(self._normalize_name(value))
            for value in values
            if value
        )

    def _singular(self, value: str) -> str:
        if value.endswith("ies") and len(value) > 3:
            return value[:-3] + "y"

        if value.endswith("es") and len(value) > 2:
            return value[:-2]

        if value.endswith("s") and len(value) > 1:
            return value[:-1]

        return value

    def _build_best_link(self, producer, consumer, target_param, produced_fields):
        best_link = None
        best_score = 0.0

        resource_name = self._resource_from_param(
            consumer.path,
            target_param.name,
        ) or self._resource_name(producer.path)

        for field in produced_fields:
            score, reason = self._score_candidate(
                producer,
                consumer,
                target_param,
                field,
            )

            if score <= best_score:
                continue

            best_score = score
            best_link = OperationLink(
                source=producer,
                target=consumer,
                source_field=field.name,
                source_json_path=field.json_path,
                state_key=f"{resource_name}.{field.name}",
                target_param=target_param.name,
                target_location=target_param.in_,
                required=target_param.required,
                fallback_state_keys=[
                    f"{resource_name}.{target_param.name}",
                    f"{resource_name}.last_id",
                ],
                confidence=score,
                reason=reason,
            )

        if best_score < self.MIN_CONFIDENCE:
            return None

        return best_link

    def _apply_config_overrides(
            self,
            graph: DependencyGraph,
            endpoints: List[Endpoint],
    ) -> None:
        for override in self.config.links:
            source = self._find_endpoint(
                endpoints,
                override.source_method,
                override.source_path,
            )
            target = self._find_endpoint(
                endpoints,
                override.target_method,
                override.target_path,
            )

            if source is None or target is None:
                continue


            graph.links.append(
                OperationLink(
                    source=source,
                    target=target,
                    source_field=self._field_from_json_path(
                        override.source_json_path
                    ),
                    source_json_path=override.source_json_path,
                    state_key=override.state_key,
                    target_param=override.target_param,
                    target_location=override.target_location,
                    required=override.required,
                    fallback_state_keys=[],
                    confidence=1.0,
                    reason="config_override",
                )
            )

    def _find_endpoint(
            self,
            endpoints: List[Endpoint],
            method: str,
            path: str,
    ) -> Endpoint | None:
        for endpoint in endpoints:
            if endpoint.method.upper() == method and endpoint.path == path:
                return endpoint
        return None

    def _field_from_json_path(self, json_path: str) -> str:
        return json_path.rstrip("]").split(".")[-1].replace("[*", "")

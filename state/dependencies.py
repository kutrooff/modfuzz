from typing import List
from dataclasses import dataclass

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
    CONSUMER_METHODS = {"GET", "PUT", "PATCH", "DELETE"}

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
                    if param.in_ == "path"
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

        self._apply_config_overrides(graph, endpoints)
        return graph

    def _is_producer(self, endpoint: Endpoint) -> bool:
        if endpoint.method.upper() not in self.PRODUCER_METHODS:
            return False

        return self._has_success_response(endpoint)

    def _is_consumer(self, endpoint: Endpoint) -> bool:
        if endpoint.method.upper() not in self.CONSUMER_METHODS:

            return False
        return any(param.in_ == "path" for param in endpoint.parameters)

    def _resource_name(self, path: str) -> str:
        parts = [part for part in path.split("/") if part and not part.startswith("{")]

        return parts[0] if parts else "resource"

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

        schema_type = schema.get("type")

        if schema_type == "object":
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
            .lower()
        )

    def _score_candidate(self, producer, consumer, target_param, field: ResponseField):
        score = 0.0
        reasons = []

        producer_resource = self._resource_name(producer.path)
        consumer_resource = self._resource_name(consumer.path)

        if producer_resource == consumer_resource:
            score += 0.40
            reasons.append("same_resource")
        else:
            score -= 0.20
            reasons.append("different_resource")

        target_name = target_param.name
        target_norm = self._normalize_name(target_name)
        field_norm = self._normalize_name(field.name)

        if target_name == field.name:
            score += 0.30
            reasons.append("exact_name_match")

        elif target_norm == field_norm:
            score += 0.25
            reasons.append("normalized_name_match")

        if target_norm.endswith("id") and field_norm == "id":
            score += 0.20
            reasons.append("id_suffix_match")

        if field_norm == "uuid":
            score += 0.15
            reasons.append("uuid_fallback")

        if field.json_path.startswith("$.data.") or field.json_path.startswith("$.result."):
            score += 0.10
            reasons.append("common_wrapper_path")

        return score, ", ".join(reasons)

    def _build_best_link(self, producer, consumer, target_param, produced_fields):
        best_link = None
        best_score = 0.0

        resource_name = self._resource_name(producer.path)

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
from typing import List

from schema.models import Endpoint
from models import DependencyGraph, OperationLink

class DependencyAnalyzer:
    """
    Строит простые зависимости между endpoint-ами.

    Первая версия:
    - producer: POST /resources с ответом, где есть id;
    - consumer: GET/PUT/PATCH/DELETE /resources/{id};
    - связь строится по совпадению первого сегмента пути.
    """

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
            producer_resource = self._resource_name(producer.path)

            for consumer in consumers:
                consumer_resource = self._resource_name(consumer.path)

                if producer_resource != consumer_resource:
                    continue

                path_params = [
                    param for param in consumer.parameters
                    if param.in_ == "path"
                ]

                for param in path_params:
                    graph.links.append(
                        OperationLink(
                            source=producer,
                            target=consumer,
                            source_field="id",
                            target_param=param.name,
                            target_location="path",
                        )
                    )

        return graph

    def _is_producer(self, endpoint: Endpoint) -> bool:
        if endpoint.method.upper() not in self.PRODUCER_METHODS:
            return False

        return any(
            200 <= status < 300
            for status in endpoint.responses.keys()
        )

    def _is_consumer(self, endpoint: Endpoint) -> bool:
        if endpoint.method.upper() not in self.CONSUMER_METHODS:

            return False
        return any(param.in_ == "path" for param in endpoint.parameters)

    def _resource_name(self, path: str) -> str:
        parts = [part for part in path.split("/") if part and not part.startswith("{")]

        return parts[0] if parts else "resource"
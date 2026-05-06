from dataclasses import dataclass, field
from typing import Any, List
from schema.models import Endpoint

@dataclass
class StateValue:
    key: str
    value: Any
    source_path: str
    source_method: str
    source_field: str


@dataclass
class OperationLink:
    """
    Описывает связь между операцией-источником и операцией-потребителем
    """

    source: Endpoint
    target: Endpoint
    source_field: str
    target_param: str
    target_location: str = "path"

@dataclass
class DependencyGraph:
    links: List[OperationLink] = field(default_factory=list)

    def consumers_for(self, endpoint: Endpoint) -> List[OperationLink]:
        return [
            link for link in self.links
            if link.source.path == endpoint.path
               and link.source.method == endpoint.method
        ]

    def producers_for(self, endpoint: Endpoint) -> List[OperationLink]:
        return [
            link for link in self.links
            if link.target.path == endpoint.path
            and link.target.method == endpoint.method
        ]
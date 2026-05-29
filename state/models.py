from dataclasses import dataclass, field
from typing import Any, List, Optional
from schema.models import Endpoint
import time

@dataclass
class StateValue:
    """
    Описывает значение текущего состояния
    """
    key: str
    value: Any
    source_path: str
    source_method: str
    source_field: str

    resource: str = ""
    value_type: str = ""
    json_path: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    request_index: Optional[int] = None


@dataclass
class OperationLink:
    """
    Описывает связь между операцией-источником и операцией-потребителем
    """
    source: Endpoint
    target: Endpoint

    source_field: str
    target_param: str

    source_json_path: str = "$.id"
    state_key: str = ""
    target_location: str = "path"
    required: bool = True
    fallback_state_keys: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""

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
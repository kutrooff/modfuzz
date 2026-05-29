from dataclasses import dataclass, field
from typing import Dict


@dataclass
class EndpointStatistics:
    total_requests: int = 0
    total_failures: int = 0

    server_errors: int = 0
    hidden_errors: int = 0
    slow_responses: int = 0

    score: float = 1.0


@dataclass
class AdaptiveContext:
    endpoint_stats: Dict[str, EndpointStatistics] = field(default_factory=dict)

    mutation_intensity: int = 1

    max_payload_size: int = 100

    repeat_failed_cases: bool = True
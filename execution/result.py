from dataclasses import  dataclass, field
from typing import Any, Dict, Optional, List

from schema.models import TestCase

@dataclass
class ExecutionResult:
    case: TestCase
    status_code: Optional[int]
    response_body: Optional[Any]
    response_headers: Dict[str, str]
    elapsed_ms: float
    success: bool
    error: Optional[str] = None
    checks: List[str] = field(default_factory=list)
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    analysis: Dict[str, Any] = field(default_factory=dict)

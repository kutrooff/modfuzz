from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourceSnapshot:
    source_method: str
    source_path: str
    status_code: int | None
    body: dict[str, Any]
    identity: Any = None


class SnapshotStore:
    def __init__(self):
        self.snapshots: list[ResourceSnapshot] = []

    def add(self, snapshot: ResourceSnapshot) -> None:
        self.snapshots.append(snapshot)

    def last(self) -> ResourceSnapshot | None:
        return self.snapshots[-1] if self.snapshots else None

    def last_by_method(self, method: str) -> ResourceSnapshot | None:
        for snapshot in reversed(self.snapshots):
            if snapshot.source_method == method:
                return snapshot
        return None

def extract_identity(body: Any) -> Any:
    if not isinstance(body, dict):
        return None

    for key in ("id", "uuid", "userId", "user_id"):
        if key in body:
            return body[key]

    data = body.get("data")
    if isinstance(data, dict):
        return extract_identity(data)

    result = body.get("result")
    if isinstance(result, dict):
        return extract_identity(result)

    return None
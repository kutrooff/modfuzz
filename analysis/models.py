from dataclasses import dataclass, field


ISSUE_PRIORITY = [
    "referential_integrity_violation",
    "invalid_state_transition",
    "cross_service_state_mismatch",
    "state_resolution_failed",
    "state_read_after_create_failed",
    "state_update_failed",
    "state_update_not_visible",
    "state_delete_failed",
    "state_delete_not_applied",
    "state_location_id_mismatch",
    "state_identity_mismatch",
    "server_error",
    "slow_response",
    "empty_response",
    "hidden_error",
    "invalid_behavior",
]


def select_primary_issue(issues: list[str]) -> str | None:
    if not issues:
        return None

    for issue in ISSUE_PRIORITY:
        if issue in issues:
            return issue

    return issues[0]


@dataclass
class AnalysisResult:

    issues: list[str] = field(default_factory=list)
    severity: str = "info"
    primary_issue: str | None = None

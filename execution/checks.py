from execution.result import ExecutionResult


def check_status_code(result: ExecutionResult) -> None:
    expected = getattr(result.case, "expected_statuses", None)

    if not expected:
        result.checks.append("status_code: skipped")
        return

    if result.status_code in expected:
        result.checks.append("status_code: passed")
    else:
        result.success = False
        result.checks.append(
            f"status_code: failed, expected {expected}, got {result.status_code}"
        )


def check_no_server_error(result: ExecutionResult) -> None:
    if result.status_code is None:
        result.success = False
        result.checks.append("server_error: failed, no response")
        return

    if result.status_code >= 500:
        result.success = False
        result.checks.append(
            f"server_error: failed, got {result.status_code}"
        )
    else:
        result.checks.append("server_error: passed")


def run_default_checks(result: ExecutionResult) -> ExecutionResult:
    check_status_code(result)
    check_no_server_error(result)
    return result
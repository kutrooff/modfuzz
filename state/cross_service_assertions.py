from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from analysis.models import AnalysisResult
from analysis.response_analyzer import ResponseAnalyzer
from execution.checks import run_default_checks
from execution.http_client import AsyncHttpExecutor
from execution.result import ExecutionResult
from schema.models import Endpoint, Parameter, TestCase
from state.config import CrossServiceAssertion, StateConfig
from state.manager import StateManager
from state.resolver import StateResolutionError, StateResolver


class CrossServiceAssertionRunner:
    def __init__(
        self,
        http_executor: AsyncHttpExecutor,
        state_manager: StateManager,
        state_config: StateConfig | None = None,
    ):
        self.http_executor = http_executor
        self.state_manager = state_manager
        self.state_config = state_config or StateConfig()
        self.resolver = StateResolver(state_manager)
        self.analyzer = ResponseAnalyzer()

    async def run_after(
        self,
        trigger_result: ExecutionResult,
    ) -> list[ExecutionResult]:
        if not self._is_successful_trigger(trigger_result):
            return []

        results = []

        for assertion in self.state_config.cross_service_assertions:
            if not self._matches_trigger(assertion, trigger_result):
                continue

            result = await self._run_assertion(assertion)
            results.append(result)

        return results

    def _is_successful_trigger(self, result: ExecutionResult) -> bool:
        return result.status_code is not None and 200 <= result.status_code < 300

    def _matches_trigger(
        self,
        assertion: CrossServiceAssertion,
        result: ExecutionResult,
    ) -> bool:
        if assertion.after_method is None or assertion.after_path is None:
            return True

        endpoint = result.case.endpoint
        return (
            endpoint.method.upper() == assertion.after_method
            and endpoint.path == assertion.after_path
        )

    async def _run_assertion(
        self,
        assertion: CrossServiceAssertion,
    ) -> ExecutionResult:
        case = self._build_case(assertion)

        try:
            resolved_case = self.resolver.resolve(case, [])
        except StateResolutionError as exc:
            result = self._resolution_error_result(case, exc)
            self._add_issue(result, assertion.issue)
            return result

        result = await self.http_executor.send(resolved_case)
        result = run_default_checks(result)
        result.analysis = self.analyzer.analyze(result)
        self._apply_assertion_expectations(result, assertion)
        return result

    def _build_case(self, assertion: CrossServiceAssertion) -> TestCase:
        path_params = {}
        query_params = dict(assertion.query or {})
        headers = dict(assertion.headers or {})
        body = deepcopy(assertion.body)

        placeholders = self._path_placeholders(assertion.request_path)
        bindings = dict(assertion.bindings or {})

        for name in placeholders:
            path_params[name] = bindings.pop(name, f"$state.{name}")

        for name, value in bindings.items():
            if body is None:
                body = {}

            if isinstance(body, dict):
                body.setdefault(name, value)

        endpoint = Endpoint(
            path=assertion.request_path,
            method=assertion.request_method,
            parameters=[
                Parameter(
                    name=name,
                    in_="path",
                    type_="string",
                    required=True,
                )
                for name in placeholders
            ],
        )

        return TestCase(
            endpoint=endpoint,
            method=assertion.request_method,
            path_params=path_params,
            query_params=query_params,
            headers=headers,
            body=body,
            expected_statuses=assertion.expected_statuses or [],
            strategy=f"cross_service_assertion:{assertion.name}",
            role="verification",
        )

    def _path_placeholders(self, path: str) -> list[str]:
        return re.findall(r"{([^{}]+)}", path)

    def _apply_assertion_expectations(
        self,
        result: ExecutionResult,
        assertion: CrossServiceAssertion,
    ) -> None:
        if assertion.expected_statuses:
            if result.status_code not in assertion.expected_statuses:
                self._add_issue(result, assertion.issue)

        if assertion.expected_body:
            if not self._body_matches(result.response_body, assertion.expected_body):
                self._add_issue(result, assertion.issue)

    def _body_matches(self, actual: Any, expected: dict[str, Any]) -> bool:
        if not isinstance(actual, dict):
            return False

        for key, expected_value in expected.items():
            actual_value = actual.get(key)

            if isinstance(expected_value, dict):
                if not self._body_matches(actual_value, expected_value):
                    return False
                continue

            if actual_value != expected_value:
                return False

        return True

    def _add_issue(self, result: ExecutionResult, issue: str) -> None:
        if issue not in result.analysis.issues:
            result.analysis.issues.append(issue)

        result.analysis.severity = "high"
        result.success = False

    def _resolution_error_result(
        self,
        case: TestCase,
        exc: StateResolutionError,
    ) -> ExecutionResult:
        return ExecutionResult(
            case=case,
            status_code=None,
            response_body=None,
            response_headers={},
            elapsed_ms=0,
            success=False,
            error=str(exc),
            request_method=case.method,
            analysis=AnalysisResult(),
        )

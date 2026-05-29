from execution.result import ExecutionResult
from analysis.models import AnalysisResult
import re

class ResponseAnalyzer:


    SEVERITY_LEVELS = {
        "info": 1,
        "medium": 2,
        "high": 3,
    }

    HIDDEN_ERROR_REGEX = re.compile(
        r"\b(error|exception|traceback|failed|failure)\b",
        re.IGNORECASE,
    )

    INVALID_BEHAVIOR_PATTERNS = [
        "warning",
        "negative",
        "accepted",
        "debug",
        "unsafe",
    ]

    def analyze(self, result: ExecutionResult) -> AnalysisResult:
        analysis = AnalysisResult()

        self._check_server_errors(result, analysis)
        self._check_slow_response(result, analysis)
        self._check_empty_response(result, analysis)
        self._check_hidden_errors(result, analysis)
        self._check_invalid_behavior(result, analysis)

        return analysis

    def _set_severity(self, analysis: AnalysisResult, severity: str):
        if self.SEVERITY_LEVELS[severity] > self.SEVERITY_LEVELS[analysis.severity]:
            analysis.severity = severity

    def _check_server_errors(self, result: ExecutionResult, analysis: AnalysisResult):
        if result.status_code is not None and result.status_code >= 500:
            analysis.issues.append("server_error")
            self._set_severity(analysis, "high")
    def _check_slow_response(self, result, analysis):
        if (result.elapsed_ms is not None and result.elapsed_ms > 2000):
            analysis.issues.append("slow_response")

            self._set_severity(analysis, "medium")

    def _check_empty_response(self, result: ExecutionResult, analysis: AnalysisResult):

        if result.status_code == 204:
            return

        if result.response_body in (None, "", {}):
            analysis.issues.append("empty_response")

    def _check_hidden_errors(self, result, analysis):
        if result.status_code != 200:
            return

        if not isinstance(result.response_body, dict):
            return

        text = str(result.response_body)

        if self.HIDDEN_ERROR_REGEX.search(text):
            analysis.issues.append("hidden_error")
            self._set_severity(analysis, "medium")

    def _check_invalid_behavior(self, result, analysis):

        body = result.response_body

        if not isinstance(body, dict):
            return

        text = str(body).lower()

        if (
            result.status_code == 200
            and any(pattern in text for pattern in self.INVALID_BEHAVIOR_PATTERNS)
        ):
            analysis.issues.append("invalid_behavior")

            self._set_severity(analysis, "medium")
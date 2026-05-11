from execution.result import ExecutionResult


class ResponseAnalyzer:

    def analyze(self, result: ExecutionResult) -> dict:
        analysis = {
            "issues": [],
            "severity": "info"
        }

        self._check_server_errors(result, analysis)
        self._check_slow_response(result, analysis)
        self._check_empty_response(result, analysis)
        self._check_hidden_errors(result, analysis)

        # НОВОЕ
        self._check_invalid_behavior(result, analysis)

        return analysis

    def _check_server_errors(self, result, analysis):
        if result.status_code is not None and result.status_code >= 500:
            analysis["issues"].append("server_error")
            analysis["severity"] = "high"

    def _check_slow_response(self, result, analysis):
        if result.elapsed_ms > 2000:
            analysis["issues"].append("slow_response")

            if analysis["severity"] != "high":
                analysis["severity"] = "medium"

    def _check_empty_response(self, result, analysis):
        if result.response_body in (None, "", {}):
            analysis["issues"].append("empty_response")

    def _check_hidden_errors(self, result, analysis):
        if not isinstance(result.response_body, dict):
            return

        text = str(result.response_body).lower()

        suspicious = [
            "error",
            "exception",
            "traceback",
            "failed",
        ]

        if (
            result.status_code == 200
            and any(word in text for word in suspicious)
        ):
            analysis["issues"].append("hidden_error")

            if analysis["severity"] != "high":
                analysis["severity"] = "medium"

    # НОВЫЙ МЕТОД
    def _check_invalid_behavior(self, result, analysis):

        body = result.response_body

        if not isinstance(body, dict):
            return

        text = str(body).lower()

        suspicious_patterns = [
            "warning",
            "negative",
            "accepted",
            "debug",
            "unsafe",
        ]

        if (
            result.status_code == 200
            and any(pattern in text for pattern in suspicious_patterns)
        ):
            analysis["issues"].append("invalid_behavior")

            if analysis["severity"] == "info":
                analysis["severity"] = "medium"
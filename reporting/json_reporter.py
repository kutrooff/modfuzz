import json

from pathlib import Path
from datetime import datetime


class JsonReporter:

    def export(
        self,
        results,
        findings_counter,
        mode: str,
        output_dir="reports"
    ):

        Path(output_dir).mkdir(
            exist_ok=True
        )

        timestamp = datetime.now().strftime("%H-%M-%S_%d-%m-%Y")

        report_name = (f"{mode}-report-{timestamp}.json")

        report_path = (Path(output_dir) / report_name)

        report = {

            "session": {

                "timestamp": timestamp,

                "total_requests": len(results),

                "total_findings": sum(
                    findings_counter.values()
                ),

                "issues": dict(
                    findings_counter
                )
            },

            "results": [
                self._serialize_result(r)
                for r in results
            ]
        }

        with open(
            report_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                report,
                f,
                indent=4,
                ensure_ascii=False
            )

        return report_path

    def _serialize_result(
        self,
        result
    ):

        return {

            "method":
                result.case.method,

            "path":
                result.case.endpoint.path,

            "status_code":
                result.status_code,

            "success":
                result.success,

            "issues":
                result.analysis.issues,

            "severity":
                result.analysis.severity,

            "request": {

                "path_params":
                    result.case.path_params,

                "query_params":
                    result.case.query_params,

                "headers":
                    result.case.headers,

                "body":
                    result.case.body
            },

            "response": {

                "body":
                    result.response_body,

                "error":
                    result.error
            }
        }
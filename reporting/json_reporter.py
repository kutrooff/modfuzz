import json

from pathlib import Path
from datetime import datetime


class JsonReporter:
    MAX_REPORTS = 15

    def export(
        self,
        results,
        findings_counter,
        mode: str,
        output_dir="reports/json"
    ):

        Path(output_dir).mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = datetime.now().strftime("%H-%M-%S_%d_%m_%Y")

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

        self._cleanup_old_reports(
            output_dir=Path(output_dir),
            pattern="*.json",
        )

        return report_path

    def _cleanup_old_reports(
        self,
        output_dir: Path,
        pattern: str,
    ):

        reports = sorted(
            output_dir.glob(pattern),
            key=lambda path: (
                path.stat().st_mtime,
                path.name,
            ),
            reverse=True,
        )

        for report in reports[self.MAX_REPORTS:]:
            try:
                report.unlink()
            except OSError:
                pass

    def _serialize_result(
        self,
        result
    ):

        return {

            "method":
                result.case.method,

            "path":
                result.case.endpoint.path,

            "iteration":
                result.iteration,

            "scenario_id":
                result.scenario_id,

            "scenario_step":
                result.scenario_step,

            "role":
                getattr(result.case, "role", "target"),

            "strategy":
                getattr(result.case, "strategy", "unknown"),

            "applied_mutations":
                getattr(result.case, "applied_mutations", []),

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

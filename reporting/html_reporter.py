import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


class HtmlReporter:
    MAX_REPORTS = 15

    ISSUE_DESCRIPTIONS = {
        "server_error": "Сервер вернул ошибку 5xx.",
        "slow_response": "Время ответа превысило допустимый порог.",
        "empty_response": "Ответ сервера оказался пустым.",
        "hidden_error": "В успешном ответе обнаружены признаки ошибки.",
        "invalid_behavior": "Ответ похож на некорректное поведение API.",
        "state_read_after_create_failed": "Созданный ресурс не удалось прочитать.",
        "state_update_failed": "Обновление ресурса не выполнилось корректно.",
        "state_delete_failed": "Удаление ресурса не выполнилось корректно.",
        "state_delete_not_applied": "Ресурс остался доступен после удаления.",
        "state_location_id_mismatch": "ID в Location не совпадает с ID в теле ответа.",
        "state_identity_mismatch": "API вернул не тот ресурс, который ожидался.",
        "state_update_not_visible": "Изменения ресурса не видны после обновления.",
    }

    def export(
        self,
        results,
        findings_counter,
        mode: str,
        output_dir="reports/html",
    ):
        if mode != "stateful":
            return None

        output_path = Path(output_dir)
        output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime("%H-%M-%S_%d_%m_%Y")
        report_path = output_path / f"{mode}-report-{timestamp}.html"

        with open(report_path, "w", encoding="utf-8") as file:
            file.write(
                self._render(
                    results=results,
                    findings_counter=findings_counter,
                    mode=mode,
                    timestamp=timestamp,
                )
            )

        self._cleanup_old_reports(
            output_dir=output_path,
            pattern="*.html",
        )

        return report_path

    def _render(self, results, findings_counter, mode: str, timestamp: str) -> str:
        problems = self._collect_problems(results)

        return f"""<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>ModFuzz stateful report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 24px;
            color: #222;
        }}
        h1, h2, h3 {{
            margin-bottom: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0 24px;
        }}
        th, td {{
            border: 1px solid #bbb;
            padding: 6px 8px;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            background: #eee;
        }}
        pre {{
            background: #f4f4f4;
            border: 1px solid #ccc;
            padding: 10px;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .problem {{
            border-top: 2px solid #444;
            padding-top: 12px;
            margin-top: 24px;
        }}
        .muted {{
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>Отчёт ModFuzz</h1>
    <p>Время формирования: <strong>{escape(timestamp)}</strong></p>
    <p>Всего запросов: <strong>{len(results)}</strong></p>
    <p>Найдено проблем: <strong>{sum(findings_counter.values())}</strong></p>

    <h2>Сводка проблем</h2>
    {self._render_problem_summary(findings_counter)}

    <h2>Проблемные запросы</h2>
    {self._render_problem_table(problems)}

    <h2>Детали проблем</h2>
    {self._render_problem_details(results, problems)}

    <h2>Выполненные stateful-сценарии</h2>
    {self._render_sequences(results)}
</body>
</html>"""

    def _render_problem_summary(self, findings_counter) -> str:
        if not findings_counter:
            return "<p>Проблемы не обнаружены.</p>"

        rows = []
        for issue, count in findings_counter.items():
            rows.append(
                "<tr>"
                f"<td>{escape(issue)}</td>"
                f"<td>{escape(self._describe_issue(issue))}</td>"
                f"<td>{count}</td>"
                "</tr>"
            )

        return (
            "<table>"
            "<tr><th>Тип проблемы</th><th>Что произошло</th><th>Количество</th></tr>"
            f"{''.join(rows)}"
            "</table>"
        )

    def _render_problem_table(self, problems) -> str:
        if not problems:
            return "<p>Проблемные запросы отсутствуют.</p>"

        rows = []
        for index, issue, result in problems:
            rows.append(
                "<tr>"
                f"<td>{index}</td>"
                f"<td>{self._value(result.iteration)}</td>"
                f"<td>{escape(str(self._value(result.scenario_id)))}</td>"
                f"<td>{self._value(result.scenario_step)}</td>"
                f"<td>{escape(issue)}</td>"
                f"<td>{escape(result.case.method)} {escape(result.case.endpoint.path)}</td>"
                f"<td>{escape(str(result.status_code))}</td>"
                "</tr>"
            )

        return (
            "<table>"
            "<tr><th>#</th><th>Итерация</th><th>Сценарий</th><th>Шаг</th>"
            "<th>Проблема</th><th>Запрос</th><th>Статус</th></tr>"
            f"{''.join(rows)}"
            "</table>"
        )

    def _render_problem_details(self, results, problems) -> str:
        if not problems:
            return "<p>Нет данных для детализации.</p>"

        blocks = []
        for index, issue, result in problems:
            blocks.append(
                f"""
<div class="problem">
    <h3>Проблема {index}: {escape(issue)}</h3>
    <p>{escape(self._describe_issue(issue))}</p>
    <p>
        Итерация: <strong>{self._value(result.iteration)}</strong>,
        сценарий: <strong>{escape(str(self._value(result.scenario_id)))}</strong>,
        шаг: <strong>{self._value(result.scenario_step)}</strong>
    </p>
    <p>Запрос: <strong>{escape(result.case.method)} {escape(result.case.endpoint.path)}</strong></p>
    <p>Фактический URL: <span class="muted">{escape(str(result.request_url or ""))}</span></p>

    <h4>Что было отправлено</h4>
    <pre>{escape(self._to_json(self._request_data(result)))}</pre>

    <h4>Что вернул сервер</h4>
    <pre>{escape(self._to_json(self._response_data(result)))}</pre>

    <h4>Предыдущие запросы этого сценария</h4>
    {self._render_previous_requests(results, result)}
</div>"""
            )

        return "".join(blocks)

    def _render_previous_requests(self, results, target) -> str:
        previous = [
            result for result in results
            if result.iteration == target.iteration
            and result.scenario_id == target.scenario_id
            and (result.scenario_step or 0) < (target.scenario_step or 0)
        ]

        if not previous:
            return "<p>До проблемного запроса в этом сценарии не было других шагов.</p>"

        return self._render_result_table(previous)

    def _render_sequences(self, results) -> str:
        if not results:
            return "<p>Запросы не выполнялись.</p>"

        blocks = []
        blocks.append(
            f"<p>Запросы были выполнены. Количество выполненных запросов: "
            f"<strong>{len(results)}</strong>.</p>"
        )

        for iteration, iteration_results in self._group_by(results, "iteration").items():
            blocks.append(f"<h3>Итерация {escape(str(iteration))}</h3>")

            for scenario_id, scenario_results in self._group_by(iteration_results, "scenario_id").items():
                blocks.append(f"<h4>Сценарий {escape(str(scenario_id))}</h4>")
                blocks.append(self._render_result_table(scenario_results))

        return "".join(blocks)

    def _render_result_table(self, results) -> str:
        rows = []
        for result in results:
            issues = ", ".join(self._issues(result)) or "нет"
            rows.append(
                "<tr>"
                f"<td>{self._value(result.scenario_step)}</td>"
                f"<td>{escape(result.case.method)}</td>"
                f"<td>{escape(result.case.endpoint.path)}</td>"
                f"<td>{escape(str(result.status_code))}</td>"
                f"<td>{escape(getattr(result.case, 'role', 'target'))}</td>"
                f"<td>{escape(issues)}</td>"
                "</tr>"
            )

        return (
            "<table>"
            "<tr><th>Шаг</th><th>Метод</th><th>Endpoint</th><th>Статус</th><th>Роль</th><th>Проблемы</th></tr>"
            f"{''.join(rows)}"
            "</table>"
        )

    def _collect_problems(self, results):
        problems = []
        index = 1

        for result in results:
            for issue in self._issues(result):
                problems.append((index, issue, result))
                index += 1

        return problems

    def _request_data(self, result):
        return {
            "method": result.request_method or result.case.method,
            "url": result.request_url,
            "expected_statuses": result.case.expected_statuses,
            "path_params": result.case.path_params,
            "query_params": result.case.query_params,
            "headers": self._redact(result.case.headers),
            "body": self._redact(result.case.body),
            "strategy": getattr(result.case, "strategy", "unknown"),
            "role": getattr(result.case, "role", "target"),
            "applied_mutations": getattr(result.case, "applied_mutations", []),
        }

    def _response_data(self, result):
        return {
            "status_code": result.status_code,
            "elapsed_ms": round(result.elapsed_ms, 2) if result.elapsed_ms is not None else None,
            "headers": self._redact(result.response_headers),
            "body": self._redact(result.response_body),
            "error": result.error,
        }

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

    def _group_by(self, results, attribute: str):
        groups = {}
        for result in results:
            groups.setdefault(getattr(result, attribute) or "unknown", []).append(result)
        return groups

    def _issues(self, result) -> list[str]:
        return list(getattr(result.analysis, "issues", []) or [])

    def _describe_issue(self, issue: str) -> str:
        return self.ISSUE_DESCRIPTIONS.get(
            issue,
            "Анализатор отметил ответ как потенциальную проблему.",
        )

    def _redact(self, value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if str(key).lower() in {"authorization", "token", "access_token", "password"}:
                    result[key] = "<redacted>"
                else:
                    result[key] = self._redact(item)
            return result

        if isinstance(value, list):
            return [self._redact(item) for item in value]

        return value

    def _to_json(self, data: Any) -> str:
        return json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    def _value(self, value):
        return value if value is not None else "unknown"

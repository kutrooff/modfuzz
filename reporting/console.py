from rich.console import Console

class ConsoleReporter:
    FINDING_LABELS = {"server_error": "Ошибка сервера",
                      "invalid_behavior": "Некорректное поведение",
                      "hidden_error": "Скрытая ошибка",
                      "empty_response": "Пустой ответ",
                      "state_read_after_create_failed": "Ресурс не читается после создания",
                      "state_update_failed": "Обновление созданного ресурса не выполнено",
                      "state_delete_failed": "Удаление созданного ресурса не выполнено",
                      "state_delete_not_applied": "Ресурс доступен после удаления",
                      "state_location_id_mismatch": "ID в Location не совпадает с body",
                      "state_identity_mismatch": "Операция вернула другой ресурс",
                      "state_update_not_visible": "Изменения не видны после обновления",
                      }

    def __init__(self):

        self.console = Console()

    def print_iteration(self, iteration: int, mutations: list[str]):

        self.console.print()

        self.console.rule(f"[bold cyan]ФАЗЗИНГ ИТЕРАЦИЯ {iteration}")

        self.console.print("[bold white]АКТИВНЫЕ МУТАЦИИ:[/bold white]", f"[magenta]{mutations}[/magenta]")

        self.console.print()


    def print_result(self, result):

        status_style = self._status_style(result.status_code)

        method_style = self._method_style(result.case.method)

        result_style = (
            "green"
            if result.success
            else "bold red"
        )

        status = (
            str(result.status_code)
            if result.status_code is not None
            else "ERR"
        )

        self.console.print(
            f"[{status_style}]"
            f"[{status}]"
            f"[/{status_style}] "
            f"[{method_style}]"
            f"{result.case.method:<7}"
            f"[/{method_style}] "
            f"{result.case.endpoint.path:<35} "
            f"[{result_style}]"
            f"{'УСПЕШНО' if result.success else 'ОШИБКА'}"
            f"[/{result_style}]"
        )


    def print_finding(self, issue_type: str, result):

        style = {
            "server_error": "bold red",
            "invalid_behavior": "yellow",
            "hidden_error": "magenta",
            "empty_response": "cyan",
        }.get(issue_type,"white")

        label = self.FINDING_LABELS.get(issue_type, issue_type)

        self.console.print(
            f"[{style}]"
            f"[!] {label.upper()}"
            f"[/{style}]"
        )

        self.console.print(
            f"{result.case.method} "
            f"{result.case.endpoint.path} "
            f"-> "
            f"{result.status_code}"
        )

        if result.error:

            self.console.print(
                f"[red]{result.error}[/red]"
            )

        self.console.print()


    def print_summary(
        self,
        total_requests: int,
        total_findings: int,
        findings_counter: dict
    ):

        self.console.print()
        self.console.rule("[bold cyan]СВОДКА СЕССИИ")

        self.console.print(
            f"[bold]Всего запросов:[/bold] "
            f"{total_requests}"
        )

        self.console.print(
            f"[bold]Найдено проблем:[/bold] "
            f"{total_findings}"
        )

        self.console.print()

        self.console.print("[bold]Типы проблем:[/bold]")

        for issue, count in findings_counter.items():

            style = (
                "red"
                if count > 0
                else "green"
            )

            label = self.FINDING_LABELS.get(issue, issue)

            self.console.print(
                f"[{style}]"
                f"{label}: {count}"
                f"[/{style}]"
            )

    # =====================================================
    # HELPERS
    # =====================================================

    def _status_style(self, status_code):

        if status_code is None:
            return "bold red"

        if 200 <= status_code < 300:
            return "green"

        if 400 <= status_code < 500:
            return "yellow"

        if status_code >= 500:
            return "bold red"

        return "white"

    def _method_style(
        self,
        method: str
    ):

        mapping = {
            "GET": "cyan",
            "POST": "green",
            "PATCH": "yellow",
            "DELETE": "red",
            "PUT": "blue",
        }

        return mapping.get(
            method,
            "white"
        )

    def print_report_saved(self, report_path):

        self.console.print()

        self.console.print(
            f"[bold green]JSON отчёт сохранён в :[/bold green] "
            f"{report_path}"
        )

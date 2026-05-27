from rich.console import Console

class ConsoleReporter:


    def __init__(self):

        self.console = Console()

    # =====================================================
    # ITERATION
    # =====================================================

    def print_iteration(
        self,
        iteration: int,
        mutations: list[str]
    ):

        self.console.print()

        self.console.rule(
            f"[bold cyan]FUZZING ITERATION {iteration}"
        )

        self.console.print(
            "[bold white]ACTIVE MUTATIONS:[/bold white]",
            f"[magenta]{mutations}[/magenta]"
        )

        self.console.print()

    # =====================================================
    # TEST RESULT
    # =====================================================

    def print_result(
        self,
        result
    ):

        status_style = self._status_style(
            result.status_code
        )

        method_style = self._method_style(
            result.case.method
        )

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
            f"{'OK' if result.success else 'FAILED'}"
            f"[/{result_style}]"
        )

    # =====================================================
    # FINDING
    # =====================================================

    def print_finding(
        self,
        issue_type: str,
        result
    ):

        style = {
            "server_error": "bold red",
            "invalid_behavior": "yellow",
            "hidden_error": "magenta",
            "empty_response": "cyan",
        }.get(
            issue_type,
            "white"
        )

        self.console.print(
            f"[{style}]"
            f"[!] {issue_type.upper()}"
            f"[/{style}]"
        )

        self.console.print(
            f"{result.case.method} "
            f"{result.case.endpoint.path} "
            f"-> "
            f"{result.status_code}"
        )

        # OPTIONAL:
        # SHOW ERROR

        if result.error:

            self.console.print(
                f"[red]{result.error}[/red]"
            )

        self.console.print()

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    def print_summary(
        self,
        total_requests: int,
        total_findings: int,
        findings_counter: dict
    ):

        self.console.print()

        self.console.rule(
            "[bold cyan]SESSION SUMMARY"
        )

        self.console.print(
            f"[bold]Total Requests:[/bold] "
            f"{total_requests}"
        )

        self.console.print(
            f"[bold]Total Findings:[/bold] "
            f"{total_findings}"
        )

        self.console.print()

        for issue, count in findings_counter.items():

            style = (
                "red"
                if count > 0
                else "green"
            )

            self.console.print(
                f"[{style}]"
                f"{issue}: {count}"
                f"[/{style}]"
            )

    # =====================================================
    # HELPERS
    # =====================================================

    def _status_style(
        self,
        status_code
    ):

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

    def print_report_saved(
            self,
            report_path
    ):

        self.console.print()

        self.console.print(
            f"[bold green]JSON отчёт сохранён в :[/bold green] "
            f"{report_path}"
        )

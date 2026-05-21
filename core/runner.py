from collections import Counter
from typing import List

from analysis.response_analyzer import ResponseAnalyzer
from execution.http_client import AsyncHttpExecutor
from generation.examples import generate_examples
from generation.randomized import generate_random_cases
from reporting.console import ConsoleReporter
from reporting.json_reporter import JsonReporter
from schema.models import Endpoint
from state.scenario_builder import StatefulScenarioBuilder
from state.stateful_executor import StatefulExecutor
from strategy.manager import AdaptiveStrategyManager


class FuzzingRunner:

    def __init__(self, base_url: str):

        self.base_url = base_url

        self.analyzer = ResponseAnalyzer()

        self.strategy_manager = (
            AdaptiveStrategyManager()
        )

        self.console = ConsoleReporter()

        self.json_reporter = JsonReporter()

    async def run_stateless(
        self,
        endpoints: List[Endpoint]
    ):

        all_results = []

        mutations = ["random"]

        async with AsyncHttpExecutor(
            self.base_url
        ) as http_executor:

            executor = StatefulExecutor(
                http_executor
            )

            for iteration in range(3):

                self.console.print_iteration(
                    iteration=iteration + 1,
                    mutations=mutations
                )

                cases = []

                cases.extend(
                    generate_examples(
                        endpoints
                    )
                )

                cases.extend(
                    generate_random_cases(
                        endpoints,
                        mutations=mutations
                    )
                )

                results = await executor.run_sequence(
                    cases
                )

                self._process_results(
                    results,
                    update_strategy=True
                )

                all_results.extend(
                    results
                )

                mutations = (
                    self.strategy_manager
                    .policy
                    .select_mutations(
                        self.strategy_manager.context,
                        {
                            "issues": (
                                self.strategy_manager
                                .get_global_issues()
                            )
                        }
                    )
                )

        self._finalize_session(
            all_results
        )

        return all_results

    async def run_stateful(
        self,
        endpoints: List[Endpoint]
    ):

        cases = []

        cases.extend(
            generate_examples(
                endpoints
            )
        )

        cases.extend(
            generate_random_cases(
                endpoints,
                n=1
            )
        )

        builder = StatefulScenarioBuilder()

        sequences = builder.build_sequences(
            cases
        )

        all_results = []

        async with AsyncHttpExecutor(
            self.base_url
        ) as http_executor:

            executor = StatefulExecutor(
                http_executor
            )

            for sequence in sequences:

                sequence_results = (
                    await executor.run_sequence(
                        sequence
                    )
                )

                self._process_results(
                    sequence_results
                )

                all_results.extend(
                    sequence_results
                )

        self._finalize_session(
            all_results
        )

        return all_results

    def _process_results(
        self,
        results,
        update_strategy: bool = False
    ):

        for result in results:

            analysis = self.analyzer.analyze(
                result
            )

            result.analysis = analysis

            self.console.print_result(
                result
            )

            issues = analysis.get(
                "issues",
                []
            )

            for issue in issues:

                self.console.print_finding(
                    issue,
                    result
                )

            if update_strategy:

                self.strategy_manager.update(
                    result,
                    analysis
                )

    def _count_findings(
        self,
        results
    ):

        findings_counter = Counter()

        for result in results:

            issues = result.analysis.get(
                "issues",
                []
            )

            for issue in issues:

                findings_counter[issue] += 1

        return findings_counter

    def _finalize_session(
        self,
        results
    ):

        findings_counter = self._count_findings(
            results
        )

        self.console.print_summary(
            total_requests=len(results),
            total_findings=sum(
                findings_counter.values()
            ),
            findings_counter=findings_counter
        )

        report_path = self.json_reporter.export(
            results=results,
            findings_counter=findings_counter
        )

        self.console.print_report_saved(
            report_path
        )
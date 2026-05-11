from collections import Counter
from typing import List

from analysis.response_analyzer import ResponseAnalyzer
from execution.http_client import AsyncHttpExecutor
from generation.examples import generate_examples
from generation.randomized import generate_random_cases
from reporting.console import ConsoleReporter
from schema.models import Endpoint
from state.scenario_builder import StatefulScenarioBuilder
from state.stateful_executor import StatefulExecutor
from strategy.manager import AdaptiveStrategyManager
from reporting.json_reporter import JsonReporter

class FuzzingRunner:

    def __init__(self, base_url: str):

        self.base_url = base_url
        self.analyzer = ResponseAnalyzer()
        self.strategy_manager = AdaptiveStrategyManager()
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

                    self.strategy_manager.update(
                        result,
                        analysis
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

        findings_counter = Counter()

        for result in all_results:

            issues = result.analysis.get(
                "issues",
                []
            )

            for issue in issues:

                findings_counter[issue] += 1

        report_path = self.json_reporter.export(
            results=all_results,
            findings_counter=findings_counter
        )

        self.console.print_report_saved(
            report_path
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

        async with AsyncHttpExecutor(
            self.base_url
        ) as http_executor:

            executor = StatefulExecutor(
                http_executor
            )

            results = []

            for sequence in sequences:

                sequence_results = (
                    await executor.run_sequence(
                        sequence
                    )
                )

                for result in sequence_results:

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

                results.extend(
                    sequence_results
                )

            findings_counter = Counter()

            for result in results:

                issues = result.analysis.get(
                    "issues",
                    []
                )

                for issue in issues:

                    findings_counter[issue] += 1

            self.console.print_summary(
                total_requests=len(results),
                total_findings=sum(
                    findings_counter.values()
                ),
                findings_counter=findings_counter
            )

            return results
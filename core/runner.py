from collections import Counter
from copy import deepcopy
from typing import List

from analysis.response_analyzer import ResponseAnalyzer
from execution.http_client import AsyncHttpExecutor
from generation.examples import generate_examples
from generation.randomized import generate_random_cases, mutation_engine
from reporting.console import ConsoleReporter
from reporting.json_reporter import JsonReporter
from schema.models import Endpoint
from state.scenario_builder import StatefulScenarioBuilder
from execution.executor import Executor
from state.stateful_executor import StatefulExecutor


class FuzzingRunner:

    def __init__(self, base_url: str):

        self.base_url = base_url

        self.analyzer = ResponseAnalyzer()

        self.console = ConsoleReporter()

        self.json_reporter = JsonReporter()

    async def run_stateless(self,endpoints: List[Endpoint]):

        all_results = []

        mutations = [
            "sql_injection",
            "xss",
            "boundary",
        ]

        async with AsyncHttpExecutor(
            self.base_url
        ) as http_executor:

            executor = Executor(http_executor)

            for iteration in range(3):

                self.console.print_iteration(
                    iteration=iteration + 1,
                    mutations=mutations)

                cases = []

                cases.extend(generate_examples(endpoints))

                cases.extend(
                    generate_random_cases(
                        endpoints,
                        mutations=mutations
                    )
                )

                results = await executor.run_cases(cases)

                self._process_results(results)

                all_results.extend(results)

        self._finalize_session(all_results, mode="stateless")

        return all_results

    async def run_stateful(
            self,
            endpoints: List[Endpoint],
    ):


        all_results = []

        mutations = [
            "sql_injection",
            "xss",
            "boundary",
        ]

        builder = StatefulScenarioBuilder()

        base_cases = generate_examples(
            endpoints
        )

        sequences = builder.build_sequences(
            base_cases
        )

        async with AsyncHttpExecutor(
                self.base_url
        ) as http_executor:

            executor = StatefulExecutor(
                http_executor
            )

            for iteration in range(3):

                self.console.print_iteration(
                    iteration=iteration + 1,
                    mutations=mutations,
                )

                for sequence in sequences:

                    mutated_sequence = []

                    for case in sequence:

                        mutated_case = deepcopy(case)

                        if mutated_case.body:
                            mutated_case.body = (
                                mutation_engine.apply_mutations(
                                    mutated_case.body,
                                    mutations,
                                )
                            )

                        mutated_sequence.append(
                            mutated_case
                        )

                    sequence_results = (
                        await executor.run_sequence(
                            mutated_sequence
                        )
                    )

                    self._process_results(
                        sequence_results
                    )

                    all_results.extend(
                        sequence_results
                    )

        self._finalize_session(
            all_results,
            mode="stateful"
        )

        return all_results


    def _process_results(self, results):

        for result in results:

            analysis = result.analysis

            result.analysis = analysis

            self.console.print_result(
                result
            )

            issues = analysis.issues

            for issue in issues:

                self.console.print_finding(
                    issue,
                    result
                )

    def _count_findings(
        self,
        results
    ):

        findings_counter = Counter()

        for result in results:

            issues = result.analysis.issues

            for issue in issues:

                findings_counter[issue] += 1

        return findings_counter

    def _finalize_session(
        self,
        results,
        mode
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
            findings_counter=findings_counter,
            mode=mode
        )

        self.console.print_report_saved(
            report_path
        )
from collections import Counter
from copy import deepcopy
import random
from typing import List

from analysis.response_analyzer import ResponseAnalyzer
from execution.http_client import AsyncHttpExecutor
from generation.boundary import generate_boundary_cases
from generation.examples import generate_examples
from generation.randomized import generate_random_cases
from reporting.console import ConsoleReporter
from reporting.json_reporter import JsonReporter
from schema.models import Endpoint
from state.scenario_builder import StatefulScenarioBuilder
from execution.executor import Executor
from state.stateful_executor import StatefulExecutor
from state.config import StateConfig
from generation.config import FuzzingConfig
from generation.case_mutator import apply_case_mutations


class FuzzingRunner:

    def __init__(self, base_url: str, fuzz_config: FuzzingConfig, state_config: StateConfig | None = None):

        self.base_url = base_url
        self.fuzz_config = fuzz_config or FuzzingConfig()
        if self.fuzz_config.seed is not None:
            random.seed(self.fuzz_config.seed)
        self.analyzer = ResponseAnalyzer()
        self.console = ConsoleReporter()
        self.json_reporter = JsonReporter()
        self.state_config = state_config

    async def run_stateless(self,endpoints: List[Endpoint]):

        all_results = []

        mutations = self.fuzz_config.mutations

        async with AsyncHttpExecutor(
            self.base_url
        ) as http_executor:

            executor = Executor(http_executor)

            filtered_endpoints = self._filter_endpoints(endpoints)

            for iteration in range(self.fuzz_config.iterations):

                self.console.print_iteration(
                    iteration=iteration + 1,
                    mutations=mutations)

                cases = []

                base_cases = self._generate_cases(filtered_endpoints)
                cases.extend(base_cases)

                if mutations:
                    cases.extend(
                        apply_case_mutations(case, self.fuzz_config)
                        for case in base_cases
                    )

                results = await executor.run_cases(cases)

                self._process_results(results)

                all_results.extend(results)

        self._finalize_session(all_results, mode="stateless")

        return all_results


    def _filter_endpoints(self, endpoints):
        config = self.fuzz_config

        result = []

        for endpoint in endpoints:
            if config.target_methods and endpoint.method.upper() not in config.target_methods:
                continue

            if config.include_paths and endpoint.path not in config.include_paths:
                continue

            if endpoint.path in config.exclude_paths:
                continue

            result.append(endpoint)

        return result


    async def run_stateful(
            self,
            endpoints: List[Endpoint],
    ):


        all_results = []

        mutations = self.fuzz_config.mutations

        builder = StatefulScenarioBuilder(state_config=self.state_config)

        base_cases = generate_examples(
            self._filter_endpoints(endpoints)
        )

        sequences = builder.build_sequences(
            base_cases
        )

        async with AsyncHttpExecutor(
                self.base_url
        ) as http_executor:

            executor = StatefulExecutor(
                http_executor,
                state_config=self.state_config,
            )

            for iteration in range(self.fuzz_config.iterations):

                self.console.print_iteration(
                    iteration=iteration + 1,
                    mutations=mutations,
                )

                for sequence in sequences:

                    mutated_sequence = []

                    for case in sequence:

                        mutated_case = deepcopy(case)

                        if self._should_mutate_case(case):
                            mutated_case = apply_case_mutations(case, self.fuzz_config)
                        else:
                            mutated_case = deepcopy(case)

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

    def _should_mutate_case(self, case):
        role = getattr(case, "role", "target")
        policy = self.fuzz_config.stateful

        if role == "setup":
            return policy.mutate_setup_requests

        if role == "target":
            return policy.mutate_target_requests

        if role == "verification":
            return policy.mutate_verification_requests

        if role == "cleanup":
            return policy.mutate_cleanup_requests

        return True

    def _generate_cases(self, endpoints: List[Endpoint]):
        cases = []
        generators = set(self.fuzz_config.generators)

        if "example" in generators:
            cases.extend(generate_examples(endpoints))

        if "random" in generators:
            cases.extend(generate_random_cases(endpoints))

        if "boundary" in generators:
            cases.extend(generate_boundary_cases(endpoints))

        return cases

from typing import List

from analysis.response_analyzer import ResponseAnalyzer
from strategy.manager import AdaptiveStrategyManager
from execution.http_client import AsyncHttpExecutor
from generation.examples import generate_examples
from generation.randomized import generate_random_cases
from schema.models import Endpoint
from state.scenario_builder import StatefulScenarioBuilder
from state.stateful_executor import StatefulExecutor


class FuzzingRunner:

    def __init__(self, base_url: str):

        self.base_url = base_url

        self.analyzer = ResponseAnalyzer()

        self.strategy_manager = AdaptiveStrategyManager()

    async def run_stateless(self, endpoints: List[Endpoint]):

        all_results = []

        mutations = ["random"]

        async with AsyncHttpExecutor(self.base_url) as http_executor:

            executor = StatefulExecutor(http_executor)

            for iteration in range(3):

                print("\n" + "=" * 80)
                print(f"FUZZING ITERATION {iteration + 1}")
                print("ACTIVE MUTATIONS:", mutations)

                cases = []

                cases.extend(generate_examples(endpoints))

                cases.extend(
                    generate_random_cases(
                        endpoints,
                        mutations=mutations,
                    )
                )

                results = await executor.run_sequence(cases)

                for result in results:
                    analysis = self.analyzer.analyze(result)

                    result.analysis = analysis

                    self.strategy_manager.update(
                        result,
                        analysis,
                    )

                    print("ADAPTIVE CONTEXT:")
                    print(self.strategy_manager.context)

                all_results.extend(results)

                mutations = self.strategy_manager.policy.select_mutations(
                    self.strategy_manager.context,
                    {
                        "issues":
                            self.strategy_manager.get_global_issues()
                    }
                )

        return all_results

    async def run_stateful(self, endpoints: List[Endpoint]):
        cases = []
        cases.extend(generate_examples(endpoints))
        cases.extend(generate_random_cases(endpoints, n=1))

        builder = StatefulScenarioBuilder()
        sequences = builder.build_sequences(cases)

        async with AsyncHttpExecutor(self.base_url) as http_executor:
            executor = StatefulExecutor(http_executor)

            results = []

            for sequence in sequences:
                sequence_results = await executor.run_sequence(sequence)
                results.extend(sequence_results)

            return results
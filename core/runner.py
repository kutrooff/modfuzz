from typing import List

from execution.http_client import AsyncHttpExecutor
from generation.examples import generate_examples
from generation.randomized import generate_random_cases
from schema.models import Endpoint
from state.scenario_builder import StatefulScenarioBuilder
from state.stateful_executor import StatefulExecutor


class FuzzingRunner:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def run_stateless(self, endpoints: List[Endpoint]):
        cases = []
        cases.extend(generate_examples(endpoints))
        cases.extend(generate_random_cases(endpoints))

        async with AsyncHttpExecutor(self.base_url) as http_executor:
            executor = StatefulExecutor(http_executor)
            return await executor.run_sequence(cases)

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
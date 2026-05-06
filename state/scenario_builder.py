from typing import List

from schema.models import Endpoint, TestCase
from state.dependencies import DependencyAnalyzer


class StatefulScenarioBuilder:
    def __init__(self):
        self.dependency_analyzer = DependencyAnalyzer()

    def build_sequences(self, test_cases: List[TestCase]) -> List[List[TestCase]]:
        endpoints = [case.endpoint for case in test_cases]
        graph = self.dependency_analyzer.analyze(endpoints)

        sequences: List[List[TestCase]] = []

        for link in graph.links:
            source_case = self._find_case(test_cases, link.source)
            target_case = self._find_case(test_cases, link.target)

            if source_case is None or target_case is None:
                continue

            target_case.path_params[link.target_param] = (
                f"$state.{self._resource_name(link.source.path)}.last_id"
            )

            sequences.append([source_case, target_case])

        return sequences

    def _find_case(self, cases: List[TestCase], endpoint: Endpoint) -> TestCase | None:
        for case in cases:
            if (
                case.endpoint.path == endpoint.path
                and case.endpoint.method == endpoint.method
            ):
                return case
        return None

    def _resource_name(self, path: str) -> str:
        parts = [part for part in path.split("/") if part and not part.startswith("{")]
        return parts[0] if parts else "resource"
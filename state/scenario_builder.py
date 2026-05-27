from typing import List
from copy import deepcopy

from schema.models import Endpoint, TestCase
from state.dependencies import DependencyAnalyzer
from state.models import OperationLink

class StatefulScenarioBuilder:
    def __init__(self):
        self.dependency_analyzer = DependencyAnalyzer()

    def build_sequences(self, test_cases: List[TestCase]) -> List[List[TestCase]]:

        endpoints = [case.endpoint for case in test_cases]
        graph = self.dependency_analyzer.analyze(endpoints)

        sequences: List[List[TestCase]] = []

        for link in graph.links:

            source_case = self._find_case(test_cases,link.source)
            target_case = self._find_case(test_cases,link.target)

            if source_case is None or target_case is None:
                continue

            source_case = deepcopy(source_case)
            target_case = deepcopy(target_case)

            self._inject_path_state(target_case, link)

            sequence = self._prepend_auth_if_needed(
                [source_case, target_case],
                test_cases,
            )

            sequences.append(sequence)

            next_links = graph.consumers_for(link.target)

            for next_link in next_links:

                next_case = self._find_case(test_cases, next_link.target)

                if next_case is None:
                    continue

                next_case = deepcopy(next_case)

                self._inject_path_state(next_case, next_link)

                extended_sequence = self._prepend_auth_if_needed([source_case,target_case,next_case], test_cases)

                sequences.append(extended_sequence)

        return sequences


    def _inject_path_state(self, case: TestCase, link: OperationLink) -> None:
        if case.path_params is None:
            case.path_params = {}

        case.path_params[link.target_param] = self._build_state_reference(link)

    def _build_state_reference(self, link: OperationLink) -> str:
        resource_name = self._resource_name(link.source.path)
        return f"$state.{resource_name}.{link.source_field}"

    def _find_case(self, cases: List[TestCase], endpoint: Endpoint) -> TestCase | None:
        for case in cases:
            if case.endpoint.path == endpoint.path and case.endpoint.method == endpoint.method:
                return case
        return None

    def _resource_name(self, path: str) -> str:
        parts = [part for part in path.split("/") if part and not part.startswith("{")]
        return parts[0] if parts else "resource"

    def _find_login_case(self, test_cases: List[TestCase]) -> TestCase | None:

        for case in test_cases:

            if case.endpoint.path == "/login":
                return deepcopy(case)

        return None

    def _is_auth_endpoint(self, endpoint: Endpoint):

        auth_paths = {
            "/login",
            "/auth/login",
            "signin",
        }

        return endpoint.path in auth_paths

    def _prepend_auth_if_needed(
            self,
            sequence: List[TestCase],
            test_cases: List[TestCase],
    ) -> List[TestCase]:

        requires_auth = any(
            case.endpoint.requires_auth
            for case in sequence
        )

        if not requires_auth:
            return sequence

        if sequence[0].endpoint.path == "/login":
            return sequence

        login_case = self._find_login_case(
            test_cases
        )

        if login_case:
            sequence.insert(
                0,
                login_case,
            )

        return sequence
from typing import List
from copy import deepcopy
from state.config import StateConfig
from schema.models import Endpoint, TestCase
from state.dependencies import DependencyAnalyzer
from state.models import OperationLink

class StatefulScenarioBuilder:
    def __init__(self, state_config: StateConfig | None = None):
        self.dependency_analyzer = DependencyAnalyzer(state_config)

    def build_sequences(self, test_cases: List[TestCase]) -> List[List[TestCase]]:
        endpoints = [case.endpoint for case in test_cases]
        graph = self.dependency_analyzer.analyze(endpoints)

        sequences: List[List[TestCase]] = []

        sequences.extend(
            self._build_lifecycle_sequences(test_cases, graph)
        )

        if not sequences:
            sequences.extend(
                self._build_dependency_pair_sequences(test_cases, graph)
            )

        return self._dedupe_sequences(sequences)

    def _inject_state_reference(self, case: TestCase, link: OperationLink) -> None:
        reference = self._build_state_reference(link)

        if link.target_location == "path":
            case.path_params[link.target_param] = reference
        elif link.target_location == "query":
            case.query_params[link.target_param] = reference
        elif link.target_location == "header":
            case.headers[link.target_param] = reference
        elif link.target_location == "body":
            if case.body is None or not isinstance(case.body, dict):
                case.body = {}
            case.body[link.target_param] = reference

    def _build_state_reference(self, link: OperationLink) -> str:
        resource_name = self._resource_name(link.source.path)
        return f"$state.{link.state_key}"

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

            if self._is_auth_endpoint(case.endpoint):
                return deepcopy(case)

        return None

    def _is_auth_endpoint(self, endpoint: Endpoint):

        auth_paths = {
            "/login",
            "/auth/login",
            "/signin",
            "/users/login",
            "/auth/signin",
        }

        return endpoint.path.lower() in auth_paths

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

    def _build_dependency_pair_sequences(
            self,
            test_cases: List[TestCase],
            graph,
    ) -> List[List[TestCase]]:
        sequences: List[List[TestCase]] = []

        for link in graph.links:
            source_case = self._find_case(test_cases, link.source)
            target_case = self._find_case(test_cases, link.target)

            if source_case is None or target_case is None:
                continue

            source_case = deepcopy(source_case)
            target_case = deepcopy(target_case)

            self._inject_state_reference(target_case, link)

            sequences.append([source_case, target_case])

        return sequences

    def _build_lifecycle_sequences(self, test_cases: List[TestCase], graph) -> List[List[TestCase]]:
        sequences = []

        for resource_cases in self._group_cases_by_resource(test_cases).values():
            sequence = self._build_lifecycle_sequence(resource_cases, graph)

            if sequence:
                sequences.append(sequence)

        return sequences

    def _build_lifecycle_sequence(self, cases: List[TestCase], graph) -> List[TestCase] | None:
        create_case = self._find_create_case(cases)
        read_case = self._find_read_case(cases)
        update_case = self._find_update_case(cases)
        delete_case = self._find_delete_case(cases)

        if create_case is None:
            return None

        sequence = [deepcopy(create_case)]

        for case in [read_case, update_case, read_case, delete_case, read_case]:
            if case is None:
                continue

            case_copy = deepcopy(case)

            if not self._inject_producer_links(case_copy, sequence[0], graph):
                continue

            sequence.append(case_copy)

        return sequence if len(sequence) > 1 else None

    def _group_cases_by_resource(self, test_cases: List[TestCase]) -> dict[str, List[TestCase]]:
        grouped = {}

        for case in test_cases:
            resource = self._resource_name(case.endpoint.path)
            grouped.setdefault(resource, []).append(case)

        return grouped

    def _find_create_case(self, cases: List[TestCase]) -> TestCase | None:
        return self._find_by_method(cases, {"POST"}, requires_path_param=False)

    def _find_read_case(self, cases: List[TestCase]) -> TestCase | None:
        return self._find_by_method(cases, {"GET"}, requires_path_param=True)

    def _find_update_case(self, cases: List[TestCase]) -> TestCase | None:
        return self._find_by_method(cases, {"PUT", "PATCH"}, requires_path_param=True)

    def _find_delete_case(self, cases: List[TestCase]) -> TestCase | None:
        return self._find_by_method(cases, {"DELETE"}, requires_path_param=True)

    def _find_by_method(
            self,
            cases: List[TestCase],
            methods: set[str],
            requires_path_param: bool,
    ) -> TestCase | None:
        for case in cases:
            has_path_param = any(
                param.in_ == "path"
                for param in case.endpoint.parameters
            )

            if case.endpoint.method.upper() in methods and has_path_param == requires_path_param:
                return case

        return None

    def _inject_producer_links(self, case, source_case, graph) -> bool:
        injected = False

        incoming_links = graph.producers_for(case.endpoint)

        for link in incoming_links:
            if (
                    link.source.path == source_case.endpoint.path
                    and link.source.method == source_case.endpoint.method
            ):
                self._inject_state_reference(case, link)
                injected = True

        return injected

    def _dedupe_sequences(self, sequences: List[List[TestCase]]) -> List[List[TestCase]]:
        seen = set()
        unique = []

        for sequence in sequences:
            key = self._sequence_key(sequence)

            if key in seen:
                continue

            seen.add(key)
            unique.append(sequence)

        return unique

    def _sequence_key(self, sequence: List[TestCase]):
        return tuple(
            (case.endpoint.method, case.endpoint.path)
            for case in sequence
        )
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

        sequences = [
            self._prepend_prerequisites(sequence, test_cases, graph)
            for sequence in sequences
        ]

        sequences = [
            self._prepend_auth_if_needed(sequence, test_cases)
            for sequence in sequences
        ]

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
        parts = [
            part for part in path.split("/")
            if part
            and not part.startswith("{")
            and part != "*"
            and not self._is_technical_segment(part)
        ]
        return parts[-1] if parts else "resource"

    def _is_technical_segment(self, value: str) -> bool:
        normalized = (
            value
            .replace("_", "")
            .replace("-", "")
            .lower()
        )

        if normalized in {"api", "rest", "gateway", "service", "services"}:
            return True

        if normalized.startswith("v") and normalized[1:].isdigit():
            return True

        return False

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

        if any(self._is_auth_endpoint(case.endpoint) for case in sequence):
            return sequence

        login_case = self._find_login_case(
            test_cases
        )

        if login_case:
            login_case.role = "setup"
            sequence.insert(
                0,
                login_case,
            )

        return sequence

    def _prepend_prerequisites(
            self,
            sequence: List[TestCase],
            test_cases: List[TestCase],
            graph,
    ) -> List[TestCase]:
        planned: List[TestCase] = []

        for case in sequence:
            self._append_prerequisites(
                case=case,
                planned=planned,
                test_cases=test_cases,
                graph=graph,
                visiting=set(),
            )

            planned.append(case)

        return planned

    def _append_prerequisites(
            self,
            case: TestCase,
            planned: List[TestCase],
            test_cases: List[TestCase],
            graph,
            visiting: set[tuple[str, str]],
    ) -> None:
        case_key = self._endpoint_key(case.endpoint)

        if case_key in visiting:
            return

        visiting.add(case_key)

        for link in graph.producers_for(case.endpoint):
            source_key = self._endpoint_key(link.source)

            if source_key == case_key:
                continue

            if self._contains_endpoint(planned, link.source):
                continue

            source_case = self._find_case(test_cases, link.source)

            if source_case is None:
                continue

            source_case = deepcopy(source_case)
            source_case.role = "setup"

            self._append_prerequisites(
                case=source_case,
                planned=planned,
                test_cases=test_cases,
                graph=graph,
                visiting=visiting,
            )

            if not self._contains_endpoint(planned, source_case.endpoint):
                planned.append(source_case)

        visiting.remove(case_key)

    def _contains_endpoint(
            self,
            cases: List[TestCase],
            endpoint: Endpoint,
    ) -> bool:
        return any(
            self._endpoint_key(case.endpoint) == self._endpoint_key(endpoint)
            for case in cases
        )

    def _endpoint_key(self, endpoint: Endpoint) -> tuple[str, str]:
        return endpoint.method.upper(), endpoint.path

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
            source_case.role = "setup"
            target_case.role = "target"

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

        create_copy = deepcopy(create_case)
        create_copy.role = "setup"

        sequence = [create_copy]

        lifecycle_steps = [
            (read_case, "verification"),
            (update_case, "target"),
            (read_case, "verification"),
            (delete_case, "cleanup"),
            (read_case, "verification"),
        ]

        for case, role in lifecycle_steps:
            if case is None:
                continue

            case_copy = deepcopy(case)
            case_copy.role = role

            if (
                    not self._inject_producer_links(case_copy, sequence[0], graph)
                    and not self._uses_same_path_template(case_copy, create_copy)
            ):
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
        create_case = self._find_by_method(cases, {"POST"}, requires_path_param=False)

        if create_case:
            return create_case

        return self._find_by_method(cases, {"POST"}, requires_path_param=True)

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

    def _uses_same_path_template(self, case: TestCase, source_case: TestCase) -> bool:
        return (
            case.endpoint.path == source_case.endpoint.path
            and case.endpoint.method.upper() == "GET"
            and source_case.endpoint.method.upper() == "POST"
        )

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


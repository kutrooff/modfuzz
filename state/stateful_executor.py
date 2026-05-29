from typing import List
from state.dependencies import DependencyAnalyzer
from execution.checks import run_default_checks
from execution.http_client import AsyncHttpExecutor
from execution.result import ExecutionResult
from schema.models import TestCase
from state.extractor import StateExtractor
from state.manager import StateManager
from state.resolver import StateResolver
from analysis.response_analyzer import ResponseAnalyzer
from strategy.manager import AdaptiveStrategyManager
from state.models import OperationLink
from state.assertions import StateAssertionAnalyzer
from state.config import StateConfig


class StatefulExecutor:
    """
    Высокоуровневый исполнитель stateful-сценариев.

    Алгоритм:
    1. Подставить сохранённые значения в TestCase.
    2. Отправить запрос через AsyncHttpExecutor.
    3. Выполнить проверки.
    4. Извлечь новые значения из ответа.
    5. Сохранить их в StateManager.
    """

    def __init__(
        self,
        http_executor: AsyncHttpExecutor,
        state_manager: StateManager | None = None,
        extractor: StateExtractor | None = None,
        resolver: StateResolver | None = None,
        state_config: StateConfig | None = None,
        ):

        self.http_executor = http_executor
        self.state_manager = state_manager or StateManager()
        self.extractor = extractor or StateExtractor()
        self.resolver = resolver or StateResolver(self.state_manager)
        self.analyzer = ResponseAnalyzer()
        self.strategy_manager = AdaptiveStrategyManager()
        self.state_assertions = StateAssertionAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer(state_config)

    async def run_case(
            self,
            case: TestCase,
            links: List[OperationLink] | None = None,
            request_index: int | None = None,
            incoming_links=None,
            outgoing_links=None,
    ) -> ExecutionResult:

        resolved_case = self.resolver.resolve(case, incoming_links or [])

        result = await self.http_executor.send(resolved_case)

        result = run_default_checks(result)
        result.analysis = self.analyzer.analyze(result)

        extracted = self.extractor.extract(result ,outgoing_links or [])
        for item in extracted:
            self.state_manager.save(
                key=item.key,
                value=item.value,
                source_path=result.case.endpoint.path,
                source_method=case.endpoint.method,
                source_field=item.source_field,
                json_path=item.json_path,
                resource=item.resource,
                request_index=request_index,
            )


        return result

    async def run_sequence(self, cases: List[TestCase]) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        self.state_manager.clear()

        graph = self.dependency_analyzer.analyze(
            [case.endpoint for case in cases]
        )

        for request_index, case in enumerate(cases):
            incoming_links = graph.producers_for(case.endpoint)
            outgoing_links = graph.consumers_for(case.endpoint)

            result = await self.run_case(
                case,
                incoming_links=incoming_links,
                outgoing_links=outgoing_links,
                request_index=request_index,
            )

            results.append(result)

            if result.status_code is None:
                break

            if result.status_code >= 500:
                break

        self.state_assertions.analyze_sequence(results)

        return results
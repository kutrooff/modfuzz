from typing import List

from execution.checks import run_default_checks
from execution.http_client import AsyncHttpExecutor
from execution.result import ExecutionResult
from schema.models import TestCase
from state.extractor import StateExtractor
from state.manager import StateManager
from state.resolver import StateResolver
from analysis.response_analyzer import ResponseAnalyzer
from strategy.manager import AdaptiveStrategyManager

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
        ):

        self.http_executor = http_executor
        self.state_manager = state_manager or StateManager()
        self.extractor = extractor or StateExtractor()
        self.resolver = resolver or StateResolver(self.state_manager)
        self.analyzer = ResponseAnalyzer()
        self.strategy_manager = AdaptiveStrategyManager()


    async def run_case(self, case: TestCase) -> ExecutionResult:
        resolved_case = self.resolver.resolve(case)

        result = await self.http_executor.send(resolved_case)

        result = run_default_checks(result)
        result.analysis = self.analyzer.analyze(result)
        extracted = self.extractor.extract(result)

        for key, value in extracted.items():
            self.state_manager.save(
                key=key,
                value=value,
                source_path=result.case.endpoint.path,
                source_method=case.endpoint.method,
                source_field=key.split(".")[-1],
            )

        return result

    async def run_sequence(self, cases: List[TestCase]) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        self.state_manager.clear()

        for case in cases:
            try:
                result = await self.run_case(case)

            except Exception:
                break

            results.append(result)

            if result.status_code is None:
                break

            if result.status_code >= 500:
                break

        return results
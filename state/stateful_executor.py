from typing import List

from execution.checks import run_default_checks
from execution.http_client import AsyncHttpExecutor
from execution.result import ExecutionResult
from schema.models import TestCase
from state.extractor import StateExtractor
from state.manager import StateManager
from state.resolver import StateResolver

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


    async def run_case(self, case: TestCase) -> ExecutionResult:
        resolved_case = self.resolver.resolve(case)

        result = await self.http_executor.send(resolved_case)

        result = run_default_checks(result)

        extracted = self.extractor.extract(result)

        for key, value in extracted.items():
            self.state_manager.save(
                key=key,
                value=value,
                source_path=result.case.endpoint.path,
                source_method=result.case.method,
                source_field=key.split(".")[-1],
            )

        return result

    async def run_sequence(self, cases: List[TestCase]) -> List[ExecutionResult]:
        results = []

        for case in cases:
            result = await self.run_case(case)
            results.append(result)

        return results
from analysis.response_analyzer import ResponseAnalyzer
from execution.checks import run_default_checks
from execution.http_client import AsyncHttpExecutor
from execution.result import ExecutionResult
from schema.models import TestCase

class Executor:

    def __init__(
        self,
        http_executor: AsyncHttpExecutor,
    ):

        self.http_executor = http_executor
        self.analyzer = ResponseAnalyzer()

    async def run_case(
        self,
        case: TestCase,
    ) -> ExecutionResult:

        result = await self.http_executor.send(
            case
        )

        result = run_default_checks(
            result
        )

        result.analysis = self.analyzer.analyze(
            result
        )

        return result

    async def run_cases(
        self,
        cases: list[TestCase],
    ) -> list[ExecutionResult]:

        results = []

        for case in cases:

            result = await self.run_case(
                case
            )

            results.append(result)

        return results

import time
from typing import Any, Dict, Optional

import httpx

from schema.models import TestCase
from execution.result import ExecutionResult

class AsyncHttpExecutor:

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        default_headers: Optional[Dict[str, str]] = None,
        verify: bool = True,
        follow_redirects: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            verify=verify,
            follow_redirects=follow_redirects,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def build_url(self, case: TestCase) -> str:
        path = case.endpoint.path

        for name, value in case.path_params.items():
            path = path.replace(f"{{{name}}}", str(value))

        return self.base_url + path

    def build_headers(self, case: TestCase) -> Dict[str, str]:
        headers = dict(self.default_headers)
        headers.update(case.headers or {})

        if case.body is not None and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        return headers

    async def send(self, case: TestCase) -> ExecutionResult:
        url = self.build_url(case)
        headers = self.build_headers(case)

        start = time.perf_counter()

        try:
            response = await self.client.request(
                method=case.method.upper(),
                url=url,
                params = case.query_params or {},
                headers=headers,
                json=case.body,
            )

            elapsed_ms = (time.perf_counter() - start) * 1000

            response_body = self._parse_response_body(response)

            result = ExecutionResult(
                case=case,
                status_code=response.status_code,
                response_body=response_body,
                response_headers=dict(response.headers),
                elapsed_ms=elapsed_ms,
                success=True,
                request_url=str(response.request.url),
                request_method=response.request.method,
            )

            return result

        except httpx.TimeoutException as exc:
            return self._error_result(case, url, "timeout", exc, start)

        except httpx.NetworkError as exc:
            return self._error_result(case, url, "network_error", exc, start)

        except httpx.HTTPError as exc:
            return self._error_result(case, url, "http_error", exc, start)

        except Exception as exc:
            return self._error_result(case, url, "unexpected_error", exc, start)

    def _parse_response_body(self, response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                return response.json()
            except ValueError:
                return response.text
        return response.text

    def _error_result(
            self,
            case: TestCase,
            url: str,
            error_type: str,
            exc: Exception,
            start: float,
    ) -> ExecutionResult:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return ExecutionResult(
            case=case,
            status_code=None,
            response_body=None,
            response_headers={},
            elapsed_ms=elapsed_ms,
            success=False,
            error=f"{error_type}: {exc}",
            request_url=url,
            request_method=case.method.upper(),
        )
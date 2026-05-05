import httpx
import asyncio
from typing import List
from schema.models import TestCase

class AsyncHttpExecutor:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.state = {}

    async def send(self, case: TestCase):
        url = self.base_url + case.endpoint.path
        for name, value in case.path_params.items():
            url = url.replace(f"{{name}}", str(value))

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=case.method,
                url=url,
                params=case.query_params,
                headers=case.headers,
                json=case.body
            )

        

from httpx import Client

class Executor:
    def execute(self, request):
        with Client() as client:
            response = client.request(
                method=request.method,
                url=request.url,
                headers=request.headers,
                json=request.body,
                params=request.params
            )
        return response.status_code, response.text
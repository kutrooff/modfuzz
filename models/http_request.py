class HTTPRequest:
    def __init__(self, method, url, headers=None, body=None, params=None):
        self.method=method
        self.url=url
        self.headers = headers or {}
        self.body = body
        self.params = params or {}
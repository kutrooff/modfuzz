class HTTPResponse:
    def __init__(self, status_code, body, headers, response_time):
        self.status_code = status_code
        self.body = body
        self.headers = headers
        self.response_time = response_time

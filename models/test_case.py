class TestCase:
    def __init__(self, requests):
        self.requests = requests # список объектов HTTPRequest
        self.results = [] # список объектов HTTPResponse
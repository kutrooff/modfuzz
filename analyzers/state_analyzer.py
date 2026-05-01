class StateAnalyzer:
    def __init__(self):
        self.history = []

    def update(self, request, response):
        self.history.append((request, response))

    def detect_anomalies(self, response):
        if response.status_code >= 500:
            return True
        return False

    def get_last_response(self, endpoint=None):
        for record in reversed(self.history):
            if endpoint is None or record["request"].url == endpoint:
                return record["response"]
        return None


class Anomaly:
    def __init__(self, request, response, reason):
        self.request = request
        self.response = response
        self.reason = reason


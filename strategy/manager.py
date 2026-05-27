from strategy.adaptive_context import AdaptiveContext
from strategy.policies import AdaptivePolicy
from strategy.scoring import EndpointScorer


class AdaptiveStrategyManager:

    def __init__(self):

        self.context = AdaptiveContext()
        self.scorer = EndpointScorer()
        self.policy = AdaptivePolicy()
        self.global_issues = []

    def update(self, result, analysis):

        endpoint_key = (
            f"{result.request_method} "
            f"{result.case.endpoint.path}"
        )

        self.scorer.update(
            self.context,
            endpoint_key,
            analysis,
        )

        self.policy.apply(
            self.context,
            analysis,
        )

        self.global_issues.extend(
            analysis.issues)
    def get_global_issues(self):

        return list(set(self.global_issues))
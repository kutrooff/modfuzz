from strategy.adaptive_context import EndpointStatistics


class EndpointScorer:

    def update(self, context, endpoint_key, analysis):

        if endpoint_key not in context.endpoint_stats:

            context.endpoint_stats[endpoint_key] = (
                EndpointStatistics()
            )

        stats = context.endpoint_stats[endpoint_key]

        stats.total_requests += 1

        issues = analysis.get("issues", [])

        if "server_error" in issues:
            stats.server_errors += 1
            stats.score += 10

        if "hidden_error" in issues:
            stats.hidden_errors += 1
            stats.score += 5

        if "slow_response" in issues:
            stats.slow_responses += 1
            stats.score += 3

        if "invalid_behavior" in issues:
            stats.score += 5

        if not issues:
            stats.score += 1
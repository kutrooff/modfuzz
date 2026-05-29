from strategy.adaptive_context import AdaptiveContext
from analysis.models import AnalysisResult

class AdaptivePolicy:

    def apply(self, context: AdaptiveContext, analysis: AnalysisResult):
        issues = analysis.issues

        if "server_error" in issues:
            context.mutation_intensity += 1

        if "slow_response" in issues:
            context.max_payload_size *= 2

        if "hidden_error" in issues:
            context.repeat_failed_cases = True

    def select_mutations(self, context, analysis: AnalysisResult):

        issues = analysis.issues

        mutations = []

        if "server_error" in issues:
            mutations.extend([
                "large_payload",
                "type_confusion",
            ])

        if "hidden_error" in issues:
            mutations.extend([
                "sql_injection",
                "xss",
            ])

        if "slow_response" in issues:
            mutations.extend([
                "deep_json",
                "large_payload",
            ])

        if "invalid_behavior" in issues:
            mutations.extend([
                "invalid_types",
                "boundary_values",
            ])

        if not mutations:
            mutations.append("random")

        return list(set(mutations))
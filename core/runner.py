from generators.schemathesis_generator import FuzzGenerator
from executors.httpx_executor import Executor
from analyzers.state_analyzer import StateAnalyzer
from models.http_response import HTTPResponse
# from strategies.adaptive_strategy import StrategyManager  # для будущей адаптивной стратегии

def run_fuzzing(schema_path, max_tests=100):
    generator = FuzzGenerator(schema_path)
    executor = Executor()
    analyzer = StateAnalyzer()
    # strategy = StrategyManager()

    history = []

    for i, test_case in enumerate(generator.generate_test_case()):
        if i >= max_tests:
            break

        # Можно позже использовать стратегию
        request = test_case  # strategy.select_test_case(test_case, analyzer)

        status, body = executor.execute(request)
        response = HTTPResponse(
            status_code=status,
            body=body,
            headers={},
            response_time=0
        )

        analyzer.update(request, response)
        history.append({"request": request, "response": response})

        if analyzer.detect_anomalies(response):
            print(f"Аномалия обнаружена в {request.url}!")

    return history
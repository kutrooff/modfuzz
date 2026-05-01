from core.runner import run_fuzzing
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запуск фаззинг-фреймворка")
    parser.add_argument("--schema", required=True, help="Путь к OpenAPI спецификации")
    parser.add_argument("--tests", type=int, default=100, help="Количество тестов")
    args = parser.parse_args()

    run_fuzzing(args.schema, max_tests=args.tests)
import asyncio
import argparse

from core.runner import FuzzingRunner
from schema.loader import load_schema
from schema.parser import parse_openapi

async def main():
    parser = argparse.ArgumentParser(
        description="Запуск модульного API fuzzing-фреймворка"
    )

    parser.add_argument("--schema", required=True, help="Путь или URL к OpenAPI-схеме")
    parser.add_argument("--base-url", required=True, help="Базовый URL тестируемого API")
    parser.add_argument(
        "--mode",
        choices=["stateless", "stateful"],
        default="stateless",
        help="Режим тестирования",
    )

    args = parser.parse_args()

    schema = load_schema(args.schema)
    endpoints = parse_openapi(schema)

    runner = FuzzingRunner(base_url=args.base_url)

    if args.mode == "stateful":
        results = await runner.run_stateful(endpoints)
    else:
        results = await runner.run_stateless(endpoints)

    for result in results:
        print("=" * 80)
        print("METHOD:", result.request_method)
        print("URL:", result.request_url)
        print("STATUS:", result.status_code)
        print("RESULT:", "OK" if result.success else "FAILED")
        print("CHECKS:", result.checks)
        print("ANALYSIS:", result.analysis)
        print("ERROR:", result.error or "")

        print("REQUEST QUERY PARAMS:", result.case.query_params)
        print("REQUEST PATH PARAMS:", result.case.path_params)
        print("REQUEST HEADERS:", result.case.headers)
        print("REQUEST BODY:", result.case.body)

        print("RESPONSE BODY:", result.response_body)


if __name__ == "__main__":
    asyncio.run(main())
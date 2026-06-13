import asyncio
import argparse

from core.runner import FuzzingRunner
from schema.loader import load_schema
from schema.parser import parse_openapi
from state.config import load_state_config
from generation.config import load_fuzz_config


async def main():

    parser = argparse.ArgumentParser(description="Модульный фреймворк для фаззинг-тестирования API")

    parser.add_argument("--schema", required=True, help="Путь или URL к OpenAPI-спецификации")

    parser.add_argument("--base-url", required=True, help="Базовый URL тестируемого API")

    parser.add_argument(
        "--mode",
        choices=["stateless", "stateful"],
        default="stateful",
        help="Режим фаззинг-тестирования",
    )

    parser.add_argument(
        "--fuzz-config",
        default=None,
        help="Путь до фаззинг-конфигурации YAML/JSON",
    )

    parser.add_argument(
        "--state-config",
        default=None,
        help="Путь к конфигурации зависимостей и состояния YAML/JSON",
    )

    args = parser.parse_args()
    fuzz_config = load_fuzz_config(args.fuzz_config)
    state_config = load_state_config(args.state_config)
    schema = load_schema(args.schema)
    endpoints = parse_openapi(schema)

    runner = FuzzingRunner(
        base_url=args.base_url,
        state_config=state_config,
        fuzz_config=fuzz_config,
    )

    if args.mode == "stateful":

        await runner.run_stateful(endpoints)
    else:
        await runner.run_stateless(endpoints)


if __name__ == "__main__":
    asyncio.run(main())

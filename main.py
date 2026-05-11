import asyncio
import argparse

from core.runner import FuzzingRunner
from schema.loader import load_schema
from schema.parser import parse_openapi


async def main():

    parser = argparse.ArgumentParser(
        description="Modular API fuzzing framework"
    )

    parser.add_argument(
        "--schema",
        required=True,
        help="Path or URL to OpenAPI schema"
    )

    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL of target API"
    )

    parser.add_argument(
        "--mode",
        choices=["stateless", "stateful"],
        default="stateless",
        help="Fuzzing mode"
    )

    args = parser.parse_args()
    schema = load_schema(args.schema)
    endpoints = parse_openapi(schema)

    runner = FuzzingRunner(
        base_url=args.base_url
    )

    if args.mode == "stateful":

        await runner.run_stateful(endpoints)
    else:
        await runner.run_stateless(endpoints)

if __name__ == "__main__":
    asyncio.run(main())
import random


def mutate_sql_injection():
    return "' OR 1=1 --"


def mutate_xss():
    return "<script>alert(1)</script>"


def mutate_large_string(size=10000):
    return "A" * size


def mutate_negative_number():
    return -random.randint(1, 1000000)


def mutate_invalid_type():
    return {"unexpected": "object"}


def mutate_boundary_number():
    return 999999999999


def mutate_deep_json(depth=10):
    result = current = {}

    for i in range(depth):
        current["nested"] = {}
        current = current["nested"]

    return result
import schemathesis

schema = schemathesis.openapi.from_path("api_schema.yaml")

@schema.parametrize()
def run_case(case):
    case.call() 
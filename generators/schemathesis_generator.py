from schemathesis import openapi

class FuzzGenerator:
    def __init(self, schema_path):
        self.schema = openapi.from_path(schema_path)

    def generate_test_case(self):
        for case in self.schema.fuzz():
            yield case
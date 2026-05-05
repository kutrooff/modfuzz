from typing import Dict, List
from validators import validate_responses, validate_paths, validate_request_bodies, validate_parameters

class SchemaAnalyzer:
    """
    Класс для анализа OpenAPI/Swagger схемы.
    """

    def __init__(self, schema: Dict):
        self.schema = schema
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def analyze(self):
        # проверяем наличие paths
        self.errors.extend(validate_paths(self.schema.get("paths", {})))

        for path, methods in self.schema.get("paths", {}).items():
            for method, info in methods.items():
                self.warnings.extend(validate_parameters(info.get("parameters", []), path, method))
                self.warnings.extend(validate_request_bodies(info.get("requestBody", {}), path, method))
                self.warnings.extend(validate_responses(info.get("responses", {}), path, method))

from typing import List, Dict

def validate_paths(paths: Dict) -> List[str]:
    """
    Проверяет наличие параметра paths в OpenAPI/Swagger схеме

    :param paths: Словарь paths из схемы OpenAPI
    :return:
        List[str]: Список ошибок, если paths отсутствуют
    """
    errors = []
    if not paths:
        errors.append("Schema не содержит paths.")
    return errors

def validate_parameters(parameters: List[Dict], path: str, method: str) -> List[str]:
    """
    Проверяет корректность HTTP запроса.F

    :param parameters: Список словарей параметров из схемы.
    :param path: URL путь endpoint
    :param method: HTTP метод endpoint
    :return:
        List[str]: Список предупреждений по параметрам.
    """

    warnings = []
    for param in parameters:
        if "name" not in param or "in" not in param:
            warnings.append(f"{method} {path}: параметр без name/in")
        if "schema" in param:
            t = param["schema"].get("type")
            if t not in ("string", "integer", "boolean", "array", "object", None):
                warnings.append(f"{method} {path}: неизвестный тип параметра {t}")
    return warnings


def validate_request_bodies(request_body: Dict, path: str, method: str) -> List[str]:
    """
    Проверяет наличие content в requestBody.

    :param request_body: Словарь requestBody из схемы OpenAPI.
    :param path: URL путь endpoint
    :param method: HTTP метод endpoint
    :return:
        List[str]: Список предупреждений по requestBody.
    """
    warnings = []
    if request_body:
        content = request_body.get("content", {})
        if not content:
            warnings.append(f"{method} {path}: requestBody без content")
    return warnings

def validate_responses(responses: Dict, path: str, method: str) -> List[str]:
    """
    Проверяет наличие description в ответах endpoint.

    :param responses:
    :param path:
    :param method:
    :return:
        List[str] Список предупреждений по respones.
    """
    warnings = []
    for status, resp in responses.items():
        if "description" not in resp:
            warnings.append(f"{method} {path}: response {status} без description")
    return warnings


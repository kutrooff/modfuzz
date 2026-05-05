# models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Parameter:
    """
    Представляет параметр HTTP запроса.

    Attributes:
        name: Имя параметра.
        in_: Место передачи параметра: 'path', 'query', 'header', 'cookie'.
        type_: Тип данных параметра: 'string', 'integer', 'boolean' и т.д.
        required: Обязательный ли параметр.
        schema: Ограничения параметра (min, max, enum, pattern и т.д.).
        example: Пример значения параметра, если указан в спецификации.
    """
    name: str
    in_: str  # 'path', 'query', 'header', 'cookie'
    type_: str  # 'string', 'integer', 'boolean'
    required: bool = False
    schema: Dict[str, Any] = field(default_factory=dict)
    example: Any = None

@dataclass
class RequestBody:
    """
    Представляет тело HTTP запроса.

    Attributes:
        content_type: MIME тип тела ('application/json' по умолчанию).
        schema: Схема структуры тела запроса.
        required: Обязательность наличия тела запроса.
    """
    content_type: str = "application/json"  # MIME тип
    schema: Dict[str, Any] = field(default_factory=dict)
    required: bool = True

@dataclass
class Response:
    """
    Представляет HTTP ответ от сервера.

    Attributes:
        status_code: HTTP код ответа (например, 200, 404, 500).
        description: Текстовое описание ответа.
        content_type: MIME тип тела ответа ('application/json' по умолчанию).
        schema: Схема структуры данных ответа.
    """
    status_code: int
    description: str = ""
    content_type: str = "application/json"
    schema: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Endpoint:
    """
    Представляет HTTP endpoint API.

    Attributes:
        path: URL путь endpoint (например, '/pet').
        method: HTTP метод ('GET', 'POST', 'PUT', 'DELETE').
        parameters: Список объектов Parameter для данного endpoint.
        request_body: Объект RequestBody или None, если тело не требуется.
        responses: Словарь HTTP код → Response.
        tags: Теги для классификации endpoint.
        summary: Краткое описание операции.
        description: Подробное описание операции.
    """
    path: str
    method: str  # 'GET', 'POST', 'PUT', 'DELETE'
    parameters: List[Parameter] = field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: Dict[int, Response] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    summary: str = ""
    description: str = ""

@dataclass
class TestCase:
    """
    Представляет тестовый случай для фаззинга API.

    Attributes:
        endpoint: Endpoint, к которому относится тест.
        method: HTTP метод теста.
        path_params: Значения path-параметров.
        query_params: Значения query-параметров.
        headers: HTTP заголовки запроса.
        body: Тело запроса (если есть).
        expected_statuses: Список ожидаемых HTTP кодов.
        strategy: Стратегия генерации теста ('example', 'boundary', 'random').
    """
    endpoint: Endpoint
    method: str
    path_params: Dict[str, Any] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Any] = None
    expected_statuses: List[int] = field(default_factory=list)
    strategy: str = "example"  # "example", "boundary", "random"
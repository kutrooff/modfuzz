import yaml
import json
from pathlib import Path
from urllib.request import urlopen


def load_schema(source: str)-> dict | list :
    """
    Загружает OpenAPI спецификацию из локального файла или URL.
    Поддерживаются JSON и YAML.
    :param source путь до спецификации.
    :return: dict | list схема OpenAPI
    """
    if source.startswith("http://") or source.startswith("https://"):
        with urlopen(source) as f:
            data = f.read()
        text = data.decode("utf-8")
    else:
        path = Path(source)
        text = path.read_text(encoding="utf-8")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Не удалось распознать схему как JSON или YAML: {e}")
from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup


def extract_jsonld(soup: BeautifulSoup) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    for script_index, script in enumerate(soup.select('script[type="application/ld+json"]')):
        try:
            value = json.loads(script.string or script.get_text() or "")
        except (json.JSONDecodeError, TypeError):
            continue
        _walk(value, f"$[{script_index}]", found)
    return found


def _walk(value: Any, path: str, output: list[tuple[str, dict[str, Any]]]) -> None:
    if isinstance(value, dict):
        output.append((path, value))
        for key, nested in value.items():
            _walk(nested, f"{path}.{key}", output)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _walk(nested, f"{path}[{index}]", output)

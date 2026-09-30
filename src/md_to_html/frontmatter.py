"""Safe YAML front-matter extraction."""

from __future__ import annotations

from typing import Any

import yaml

from .exceptions import FrontMatterError

_ALLOWED_METADATA = {"title", "author", "date", "lang"}


def extract_front_matter(markdown_text: str) -> tuple[dict[str, object], str]:
    """Return front-matter metadata and Markdown body.

    A document is considered to have front matter only when its first logical line is
    exactly ``---``. YAML is parsed with ``safe_load`` and must be a mapping.
    """

    normalized = markdown_text.removeprefix("\ufeff")
    lines = normalized.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return {}, normalized

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") in {"---", "..."}:
            closing_index = index
            break
    if closing_index is None:
        raise FrontMatterError("YAML 프런트매터의 닫는 구분자(---)가 없습니다.")

    yaml_source = "".join(lines[1:closing_index])
    try:
        loaded: Any = yaml.safe_load(yaml_source)
    except yaml.YAMLError as exc:
        raise FrontMatterError(f"YAML 프런트매터를 해석할 수 없습니다: {exc}") from exc

    if loaded is None:
        metadata: dict[str, object] = {}
    elif not isinstance(loaded, dict):
        raise FrontMatterError("YAML 프런트매터는 키-값 매핑이어야 합니다.")
    else:
        metadata = {}
        for key, value in loaded.items():
            if not isinstance(key, str):
                raise FrontMatterError("YAML 프런트매터 키는 문자열이어야 합니다.")
            if key in _ALLOWED_METADATA:
                metadata[key] = value

    body = "".join(lines[closing_index + 1 :])
    return metadata, body

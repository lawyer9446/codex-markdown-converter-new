"""Offline LaTeX-to-MathML rendering for dollar-delimited Markdown."""

from __future__ import annotations

from typing import Any

from latex2mathml.converter import convert

from .exceptions import MathConversionError


def render_math(source: str, options: dict[str, Any]) -> str:
    """Render math without letting TeX text introduce HTML markup.

    The final document sanitizer separately removes unsafe attributes, including
    URLs and styles emitted by LaTeX commands.
    """

    escaped = source.replace("<", "&lt;").replace(">", "&gt;")
    try:
        return str(convert(escaped, display="block" if options["display_mode"] else "inline"))
    except Exception as exc:
        # latex2mathml exposes multiple unrelated exception types. Normalize them
        # at this library boundary so both API and CLI use our error contract.
        raise MathConversionError("LaTeX 수식을 변환할 수 없습니다.") from exc

"""Typed input and output models used by the public API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class ConversionOptions:
    """Options controlling Markdown conversion.

    ``sanitize`` remains explicit for API readability, but disabling it is rejected:
    this package deliberately has no unsafe sanitizer-off mode.
    """

    standalone: bool = True
    sanitize: bool = True
    toc: bool = False
    toc_min_level: int = 2
    toc_max_level: int = 4
    lang: str | None = None
    title: str | None = None
    fallback_title: str | None = None
    allow_raw_html: bool = False
    external_links_new_tab: bool = False
    check_links: bool = False
    source_path: Path | None = None
    css_href: str | None = None
    embedded_css: str | None = None
    no_style: bool = False
    math: bool = False


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """The rendered HTML plus immutable metadata and non-fatal warnings."""

    html: str
    metadata: Mapping[str, object]
    warnings: tuple[str, ...] = ()
    output_path: Path | None = None

    @classmethod
    def create(
        cls,
        *,
        html: str,
        metadata: Mapping[str, object],
        warnings: tuple[str, ...] = (),
        output_path: Path | None = None,
    ) -> ConversionResult:
        """Create a result with a read-only copy of ``metadata``."""

        return cls(
            html=html,
            metadata=MappingProxyType(dict(metadata)),
            warnings=warnings,
            output_path=output_path,
        )

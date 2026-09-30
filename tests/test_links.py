from __future__ import annotations

from pathlib import Path

import pytest

from md_to_html import ConversionOptions, markdown_to_html
from md_to_html.links import rewrite_markdown_link


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("guide/install.md", "guide/install.html"),
        ("../intro.markdown#시작", "../intro.html#시작"),
        ("guide.MD?x=1#part", "guide.html?x=1#part"),
        ("https://example.com/manual.md", "https://example.com/manual.md"),
        ("//example.com/manual.md", "//example.com/manual.md"),
        ("mailto:user@example.com", "mailto:user@example.com"),
        ("#section", "#section"),
    ],
)
def test_rewrite_markdown_link(original: str, expected: str) -> None:
    assert rewrite_markdown_link(original) == expected


def test_link_check_reports_only_missing_local_targets(tmp_path: Path) -> None:
    source = tmp_path / "index.md"
    existing = tmp_path / "exists.md"
    existing.write_text("ok", encoding="utf-8")
    options = ConversionOptions(check_links=True, source_path=source)
    result = markdown_to_html(
        "[ok](exists.md) [missing](missing.md) ![no](image.png)", options=options
    )
    assert len(result.warnings) == 2
    assert any("missing.md" in warning for warning in result.warnings)
    assert any("image.png" in warning for warning in result.warnings)

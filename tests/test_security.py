from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from md_to_html import ConversionOptions, markdown_to_html


@pytest.mark.parametrize(
    "payload",
    [
        '<script>alert("x")</script>',
        '<img src="x" onerror="alert(1)">',
        '<a href="JaVaScRiPt:alert(1)" onclick="alert(2)">bad</a>',
        '<iframe src="https://evil.example"></iframe>',
    ],
)
def test_raw_html_cannot_create_active_content(payload: str) -> None:
    result = markdown_to_html(payload, options=ConversionOptions(allow_raw_html=True))
    soup = BeautifulSoup(result.html, "html.parser")
    assert soup.find("script") is None
    assert soup.find("iframe") is None
    assert not soup.select("[onerror], [onclick], [onload]")
    for tag in soup.find_all(href=True):
        assert not str(tag["href"]).casefold().startswith("javascript:")


def test_raw_html_is_text_by_default() -> None:
    result = markdown_to_html("<em>not raw</em>")
    soup = BeautifulSoup(result.html, "html.parser")
    assert soup.em is None
    assert "<em>not raw</em>" in soup.get_text()


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "java&#x73;cript:alert(1)",
        "vbscript:msgbox(1)",
        "data:text/html,<script>alert(1)</script>",
    ],
)
def test_dangerous_markdown_links_do_not_survive(url: str) -> None:
    result = markdown_to_html(f"[위험]({url})")
    soup = BeautifulSoup(result.html, "html.parser")
    for anchor in soup.find_all("a"):
        href = anchor.get("href", "")
        assert not href.casefold().startswith(("javascript:", "vbscript:", "data:"))


def test_style_end_in_embedded_css_cannot_escape_head() -> None:
    result = markdown_to_html(
        "safe",
        options=ConversionOptions(embedded_css="body{} </style><script>x</script>"),
    )
    soup = BeautifulSoup(result.html, "html.parser")
    assert soup.find("script") is None

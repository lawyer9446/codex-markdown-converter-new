from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from md_to_html import ConversionOptions, MathConversionError, markdown_to_html
from md_to_html.cli import main


def render(source: str, **kwargs: object) -> BeautifulSoup:
    result = markdown_to_html(source, options=ConversionOptions(math=True, **kwargs))
    return BeautifulSoup(result.html, "html.parser")


def test_inline_and_block_math_render_offline() -> None:
    soup = render(r"에너지 $E=mc^2$" + "\n\n$$\n" + r"\frac{a}{b}+\sqrt{x}" + "\n$$")
    inline, block = soup.find_all("math")
    assert inline["display"] == "inline"
    assert inline.find("msup") is not None
    assert block["display"] == "block"
    assert block.find("mfrac") is not None
    assert block.find("msqrt") is not None
    assert soup.find("script") is None


def test_math_is_opt_in() -> None:
    soup = BeautifulSoup(markdown_to_html("$x^2$").html, "html.parser")
    assert soup.find("math") is None
    assert "$x^2$" in soup.get_text()


def test_code_escaped_dollars_currency_and_unclosed_math_are_preserved() -> None:
    soup = render("`$x$`\n\n```text\n$$x$$\n```\n\n" + r"\$x\$ 비용 $5 와 $10; $unclosed")
    assert soup.find("math") is None
    assert soup.code is not None and soup.code.get_text() == "$x$"
    assert "$5 와 $10" in soup.get_text()


def test_math_in_fragment_table_and_heading() -> None:
    soup = render("# 공식 $x^2$\n\n| 공식 |\n| --- |\n| $x_i$ |", standalone=False)
    assert soup.html is None
    assert soup.h1 is not None and soup.h1.find("math") is not None
    assert soup.td is not None and soup.td.find("msub") is not None
    standalone = render("# 공식 $x^2$")
    assert standalone.title is not None and standalone.title.get_text() == "공식 x^2"


@pytest.mark.parametrize("raw_html", [False, True])
@pytest.mark.parametrize(
    "source",
    [
        r'$\text{<img src=x onerror="alert(1)">}$',
        r"$\text{<script>alert(1)</script>}$",
        r"$\href{javascript:alert(1)}{x}$",
        r"$\style{background:url(javascript:alert(1))}{x}$",
    ],
)
def test_math_cannot_inject_active_content(source: str, raw_html: bool) -> None:
    soup = render(source, allow_raw_html=raw_html)
    assert soup.find("math") is not None
    assert not soup.select("script, img, iframe, [href], [style], [onerror], [onclick]")


def test_invalid_math_uses_public_error_contract() -> None:
    with pytest.raises(MathConversionError, match="LaTeX"):
        markdown_to_html(r"$\frac{$", options=ConversionOptions(math=True))


def test_cli_math_and_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "math.md"
    source.write_text(r"$x^2$", encoding="utf-8")
    assert main([str(source), "--math", "--stdout"]) == 0
    soup = BeautifulSoup(capsys.readouterr().out, "html.parser")
    assert soup.find("msup") is not None
    source.write_text(r"$\frac{$", encoding="utf-8")
    assert main([str(source), "--math", "--stdout"]) == 1
    output = capsys.readouterr()
    assert "LaTeX" in output.err
    assert "Traceback" not in output.err

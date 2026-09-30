from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from md_to_html import ConfigurationError, ConversionOptions, markdown_to_html


def soup_for(markdown: str, **options: object) -> BeautifulSoup:
    result = markdown_to_html(markdown, options=ConversionOptions(**options))
    return BeautifulSoup(result.html, "html.parser")


def test_basic_document_uses_first_h1_as_title() -> None:
    soup = soup_for("# 프로젝트 안내\n\n이것은 **중요**합니다.")
    assert soup.title is not None and soup.title.string == "프로젝트 안내"
    assert soup.html is not None and soup.html.get("lang") == "ko"
    assert soup.h1 is not None and soup.h1.get("id") == "프로젝트-안내"
    assert soup.strong is not None and soup.strong.string == "중요"


def test_fragment_omits_document_wrapper_and_styles() -> None:
    result = markdown_to_html("# 제목", options=ConversionOptions(standalone=False))
    assert "<!doctype html>" not in result.html
    assert "<style>" not in result.html
    assert result.html.startswith('<h1 id="제목">')


def test_title_precedence_and_escaping() -> None:
    markdown = "---\ntitle: Front title\n---\n# Heading"
    result = markdown_to_html(markdown, options=ConversionOptions(title='<Admin & "owner">'))
    assert "<title>&lt;Admin &amp; &quot;owner&quot;&gt;</title>" in result.html


def test_front_matter_title_and_language() -> None:
    markdown = "---\ntitle: 배포 체크리스트\nlang: en\nauthor: 홍길동\n---\n# 릴리스"
    result = markdown_to_html(markdown)
    soup = BeautifulSoup(result.html, "html.parser")
    assert soup.title is not None and soup.title.string == "배포 체크리스트"
    assert soup.html is not None and soup.html.get("lang") == "en"
    assert result.metadata["author"] == "홍길동"
    with pytest.raises(TypeError):
        result.metadata["author"] = "변경"  # type: ignore[index]


def test_gfm_table_task_list_strikethrough_and_footnote() -> None:
    markdown = """
| 작업 | 상태 |
| --- | --- |
| 테스트 | 완료 |

- [x] 테스트 실행
- [ ] 배포

~~폐기~~ [^note]

[^note]: 각주입니다.
"""
    soup = soup_for(markdown)
    assert soup.table is not None
    assert [cell.get_text(strip=True) for cell in soup.select("th")] == ["작업", "상태"]
    checkboxes = soup.select('input[type="checkbox"]')
    assert len(checkboxes) == 2
    assert all(box.has_attr("disabled") for box in checkboxes)
    assert checkboxes[0].has_attr("checked")
    assert soup.del_ is None  # BeautifulSoup reserves the Python name; select instead.
    assert soup.select_one("del").get_text() == "폐기"  # type: ignore[union-attr]
    assert soup.select_one("section.footnotes") is not None


def test_known_and_unknown_code_fences_are_safe() -> None:
    markdown = """```python
value = "<strong>Hello</strong>"
```

```unknown-language
<script>alert(1)</script>
```
"""
    soup = soup_for(markdown)
    assert soup.select_one("pre.highlight code.language-python") is not None
    assert not soup.find_all("script")
    code_text = soup.find_all("code")[-1].get_text()
    assert "<script>alert(1)</script>" in code_text


def test_duplicate_and_empty_heading_ids_are_stable() -> None:
    soup = soup_for("# 설치\n\n## 설치\n\n## !!!\n\n## !!!")
    assert [heading.get("id") for heading in soup.select("h1, h2")] == [
        "설치",
        "설치-2",
        "section",
        "section-2",
    ]


def test_toc_links_match_heading_ids() -> None:
    soup = soup_for("# API\n\n## 설치\n\n### 세부\n\n## 설치", toc=True)
    links = soup.select("nav.table-of-contents a")
    assert [link.get("href") for link in links] == ["#설치", "#세부", "#설치-2"]
    assert all(soup.select_one(link["href"]) is not None for link in links)
    assert soup.select_one("nav.table-of-contents ul ul") is not None


def test_formatted_heading_uses_visible_text_for_title_and_toc() -> None:
    soup = soup_for("# **Project** `API`\n\n## [Install](guide.md)", toc=True)
    assert soup.title is not None and soup.title.string == "Project API"
    assert soup.h1 is not None and soup.h1.get("id") == "project-api"
    toc_link = soup.select_one("nav.table-of-contents a")
    assert toc_link is not None and toc_link.get_text() == "Install"


def test_external_link_attributes_are_added() -> None:
    soup = soup_for(
        "[외부](https://example.com/docs) [메일](mailto:user@example.com)",
        external_links_new_tab=True,
    )
    external = soup.find("a", href="https://example.com/docs")
    assert external is not None
    assert set(external.get("rel", [])) == {"noopener", "noreferrer"}
    assert external.get("target") == "_blank"
    mail = soup.find("a", href="mailto:user@example.com")
    assert mail is not None and not mail.has_attr("target")


def test_images_are_lazy_and_alt_text_is_preserved() -> None:
    soup = soup_for("![설명 <unsafe>](image.png)")
    image = soup.img
    assert image is not None
    assert image.get("loading") == "lazy"
    assert image.get("alt") == "설명 <unsafe>"


def test_custom_and_default_styles() -> None:
    default = markdown_to_html("text").html
    custom = markdown_to_html(
        "text", options=ConversionOptions(embedded_css="body { color: red; }")
    ).html
    external = markdown_to_html("text", options=ConversionOptions(css_href="/assets/site.css")).html
    assert "font: 16px" in default
    assert "body { color: red; }" in custom
    assert '<link rel="stylesheet" href="/assets/site.css">' in external


@pytest.mark.parametrize(
    "options",
    [
        ConversionOptions(sanitize=False),
        ConversionOptions(toc_min_level=5, toc_max_level=2),
        ConversionOptions(css_href="x.css", no_style=True),
        ConversionOptions(css_href="javascript:alert(1)"),
    ],
)
def test_invalid_options_are_rejected(options: ConversionOptions) -> None:
    with pytest.raises(ConfigurationError):
        markdown_to_html("# test", options=options)


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_line_endings_and_unicode(line_ending: str) -> None:
    source = line_ending.join(["# 한글 🚀", "", "문단입니다."])
    soup = soup_for(source)
    assert soup.h1 is not None and soup.h1.get_text() == "한글 🚀"
    assert "문단입니다." in soup.get_text()

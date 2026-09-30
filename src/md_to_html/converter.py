"""Core Markdown rendering and file-conversion APIs."""

from __future__ import annotations

import html
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from .exceptions import ConfigurationError, InputFileError, OutputFileError
from .frontmatter import extract_front_matter
from .links import is_dangerous_url, process_inline_tokens
from .models import ConversionOptions, ConversionResult
from .security import sanitize_html
from .styles import DEFAULT_CSS

_SUPPORTED_SUFFIXES = {".md", ".markdown"}
_NON_WORD = re.compile(r"[^\w\- ]+", re.UNICODE)
_SEPARATORS = re.compile(r"[\s_\-]+", re.UNICODE)
_STYLE_END = re.compile(r"</style", re.IGNORECASE)


@dataclass(slots=True)
class _TocNode:
    level: int
    identifier: str
    label: str
    children: list[_TocNode] = field(default_factory=list)


def _highlight_code(code: str, language: str, _attributes: str) -> str:
    """Render a known fenced-code language or ask markdown-it to fall back."""

    if not language:
        return ""
    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        return ""
    formatter = HtmlFormatter(nowrap=True)
    highlighted = highlight(code, lexer, formatter)
    safe_language = html.escape(language, quote=True)
    return (
        f'<pre class="highlight"><code class="language-{safe_language}">{highlighted}</code></pre>'
    )


def _build_markdown(options: ConversionOptions) -> MarkdownIt:
    parser = MarkdownIt(
        "commonmark",
        {
            "html": options.allow_raw_html,
            "linkify": True,
            "highlight": _highlight_code,
        },
    )
    parser.enable(["table", "strikethrough", "linkify"])
    parser.use(tasklists_plugin)
    parser.use(footnote_plugin)
    return parser


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip().casefold()
    without_punctuation = _NON_WORD.sub("", normalized)
    slug = _SEPARATORS.sub("-", without_punctuation).strip("-")
    return slug or "section"


def _inline_plain_text(token: Token) -> str:
    """Extract visible heading text without Markdown delimiter syntax."""

    if token.type in {"text", "code_inline"}:
        return token.content
    if token.type == "image":
        return token.content
    if token.type in {"softbreak", "hardbreak"}:
        return " "
    if token.children:
        return "".join(_inline_plain_text(child) for child in token.children)
    return ""


def _add_heading_ids(tokens: list[Token]) -> tuple[list[tuple[int, str, str]], str | None]:
    counts: dict[str, int] = {}
    headings: list[tuple[int, str, str]] = []
    first_h1: str | None = None
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or index + 1 >= len(tokens):
            continue
        inline = tokens[index + 1]
        if inline.type != "inline":
            continue
        label = _inline_plain_text(inline).strip()
        base = _slugify(label)
        counts[base] = counts.get(base, 0) + 1
        heading_id = base if counts[base] == 1 else f"{base}-{counts[base]}"
        token.attrSet("id", heading_id)
        level = int(token.tag.removeprefix("h"))
        headings.append((level, heading_id, label))
        if level == 1 and first_h1 is None:
            first_h1 = label
    return headings, first_h1


def _normalize_semantic_tags(tokens: list[Token]) -> None:
    """Prefer semantic HTML tags where markdown-it's GFM rule uses aliases."""

    for token in tokens:
        if token.type in {"s_open", "s_close"}:
            token.tag = "del"
        if token.children:
            _normalize_semantic_tags(token.children)


def _render_toc(headings: list[tuple[int, str, str]], min_level: int, max_level: int) -> str:
    selected = [item for item in headings if min_level <= item[0] <= max_level]
    if not selected:
        return ""

    roots: list[_TocNode] = []
    stack: list[_TocNode] = []
    for level, identifier, label in selected:
        node = _TocNode(level=level, identifier=identifier, label=label)
        while stack and stack[-1].level >= level:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)

    def render_nodes(nodes: list[_TocNode]) -> str:
        items: list[str] = []
        for node in nodes:
            child_html = f"\n{render_nodes(node.children)}" if node.children else ""
            items.append(
                f'<li class="toc-level-{node.level}"><a href="#'
                f'{html.escape(node.identifier, quote=True)}">{html.escape(node.label)}</a>'
                f"{child_html}</li>"
            )
        joined_items = "\n".join(items)
        return f"<ul>\n{joined_items}\n</ul>"

    return f'<nav class="table-of-contents" aria-label="목차">\n{render_nodes(roots)}\n</nav>\n'


def _validate_options(options: ConversionOptions) -> None:
    if not options.sanitize:
        raise ConfigurationError("HTML 정화 기능은 보안상 비활성화할 수 없습니다.")
    if not 1 <= options.toc_min_level <= options.toc_max_level <= 6:
        raise ConfigurationError("목차 제목 수준은 1부터 6 사이의 올바른 범위여야 합니다.")
    style_count = sum(
        (options.css_href is not None, options.embedded_css is not None, options.no_style)
    )
    if style_count > 1:
        raise ConfigurationError("외부 CSS, 인라인 CSS, 스타일 없음은 함께 사용할 수 없습니다.")
    if options.css_href is not None and is_dangerous_url(options.css_href):
        raise ConfigurationError("CSS URL에 위험한 scheme을 사용할 수 없습니다.")


def _metadata_text(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        return str(value)
    # PyYAML commonly produces date/datetime instances; their string form is stable.
    if value.__class__.__module__ == "datetime":
        return str(value)
    raise ConfigurationError(f"프런트매터의 {key!r} 값은 단순한 문자열이어야 합니다.")


def _safe_embedded_css(css: str) -> str:
    # CSS files are explicit local inputs, but prevent them from escaping the style tag.
    return _STYLE_END.sub(r"<\\/style", css)


def _standalone_document(
    body: str,
    *,
    title: str,
    lang: str,
    options: ConversionOptions,
) -> str:
    style_markup = ""
    if not options.no_style:
        if options.css_href is not None:
            style_markup = (
                f'  <link rel="stylesheet" href="{html.escape(options.css_href, quote=True)}">\n'
            )
        else:
            css = options.embedded_css if options.embedded_css is not None else DEFAULT_CSS
            style_markup = f"  <style>\n{_safe_embedded_css(css)}\n  </style>\n"
    return (
        "<!doctype html>\n"
        f'<html lang="{html.escape(lang, quote=True)}">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{html.escape(title)}</title>\n"
        f"{style_markup}"
        "</head>\n"
        "<body>\n"
        f"{body.rstrip()}\n"
        "</body>\n"
        "</html>\n"
    )


def markdown_to_html(
    markdown_text: str,
    *,
    options: ConversionOptions | None = None,
) -> ConversionResult:
    """Convert a Markdown string into sanitized HTML without file I/O."""

    active_options = options or ConversionOptions()
    _validate_options(active_options)
    metadata, body_source = extract_front_matter(markdown_text)
    parser = _build_markdown(active_options)
    environment: dict[str, Any] = {}
    tokens = parser.parse(body_source, environment)
    _normalize_semantic_tags(tokens)
    headings, first_h1 = _add_heading_ids(tokens)
    warnings = process_inline_tokens(
        tokens,
        external_links_new_tab=active_options.external_links_new_tab,
        check_links=active_options.check_links,
        source_path=active_options.source_path,
    )
    body = parser.renderer.render(tokens, parser.options, environment)
    if active_options.toc:
        body = (
            _render_toc(headings, active_options.toc_min_level, active_options.toc_max_level) + body
        )
    body = sanitize_html(body)

    metadata_title = _metadata_text(metadata, "title")
    title = (
        active_options.title
        or metadata_title
        or first_h1
        or active_options.fallback_title
        or "Document"
    )
    metadata_lang = _metadata_text(metadata, "lang")
    lang = active_options.lang or metadata_lang or "ko"
    rendered = (
        _standalone_document(body, title=title, lang=lang, options=active_options)
        if active_options.standalone
        else f"{body.rstrip()}\n"
    )
    return ConversionResult.create(html=rendered, metadata=metadata, warnings=warnings)


def _atomic_write(path: Path, content: str, *, overwrite: bool, encoding: str) -> None:
    if path.is_symlink():
        raise OutputFileError(f"심볼릭 링크 출력 경로에는 쓸 수 없습니다: {path}")
    if path.exists() and not overwrite:
        raise OutputFileError(
            f"출력 파일이 이미 존재합니다: {path} (--overwrite로 덮어쓸 수 있습니다)"
        )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding=encoding, newline="\n") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists() and not overwrite:
                raise OutputFileError(f"출력 파일이 변환 중 생성되었습니다: {path}")
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)
    except OutputFileError:
        raise
    except OSError as exc:
        raise OutputFileError(f"출력 파일을 쓸 수 없습니다: {path}: {exc}") from exc


def _read_markdown_file(source: Path, encoding: str) -> str:
    if source.is_symlink():
        raise InputFileError(f"심볼릭 링크 입력 파일은 처리하지 않습니다: {source}")
    if not source.is_file():
        raise InputFileError(f"입력 파일이 존재하지 않습니다: {source}")
    if source.suffix.casefold() not in _SUPPORTED_SUFFIXES:
        raise InputFileError(f"지원하지 않는 입력 확장자입니다: {source.suffix}")
    try:
        return source.read_text(encoding=encoding)
    except (OSError, UnicodeError, LookupError) as exc:
        raise InputFileError(f"입력 파일을 읽을 수 없습니다: {source}: {exc}") from exc


def convert_file(
    input_path: Path,
    output_path: Path | None = None,
    *,
    options: ConversionOptions | None = None,
    overwrite: bool = False,
    encoding: str = "utf-8",
) -> ConversionResult:
    """Read, convert, and atomically write one Markdown file."""

    source = Path(input_path)
    markdown_text = _read_markdown_file(source, encoding)

    destination = Path(output_path) if output_path is not None else source.with_suffix(".html")
    base_options = options or ConversionOptions()
    file_options = replace(
        base_options,
        source_path=source,
        fallback_title=base_options.fallback_title or source.stem,
    )
    converted = markdown_to_html(markdown_text, options=file_options)
    _atomic_write(destination, converted.html, overwrite=overwrite, encoding=encoding)
    return ConversionResult.create(
        html=converted.html,
        metadata=converted.metadata,
        warnings=converted.warnings,
        output_path=destination,
    )

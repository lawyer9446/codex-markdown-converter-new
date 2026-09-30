"""URL classification and local Markdown-link rewriting."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import SplitResult, unquote, urlsplit, urlunsplit

from markdown_it.token import Token

_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_EXTERNAL_SCHEMES = {"http", "https"}
_DANGEROUS_SCHEMES = {"javascript", "vbscript", "data"}
_CONTROL_OR_SPACE = re.compile(r"[\x00-\x20\x7f]+")


def _normalized_scheme(url: str) -> str:
    prefix = url.split(":", 1)[0] if ":" in url else ""
    return _CONTROL_OR_SPACE.sub("", prefix).casefold()


def is_dangerous_url(url: str) -> bool:
    """Return whether ``url`` starts with a disallowed active-content scheme."""

    return _normalized_scheme(url) in _DANGEROUS_SCHEMES


def is_external_url(url: str) -> bool:
    """Return whether ``url`` is an HTTP(S) network URL."""

    parsed = urlsplit(url)
    return parsed.scheme.casefold() in _EXTERNAL_SCHEMES and bool(parsed.netloc)


def rewrite_markdown_link(url: str) -> str:
    """Change a relative ``.md``/``.markdown`` path to ``.html``.

    Query strings and fragments are preserved. Absolute network URLs, scheme-relative
    URLs, mail links, and fragment-only links are left unchanged.
    """

    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return url
    path = Path(parsed.path)
    if path.suffix.casefold() not in _MARKDOWN_SUFFIXES:
        return url
    rewritten = parsed._replace(path=str(path.with_suffix(".html")).replace("\\", "/"))
    return urlunsplit(rewritten)


def _merge_rel(existing: str | None) -> str:
    values = set(existing.split() if existing else ())
    values.update({"noopener", "noreferrer"})
    return " ".join(sorted(values))


def _attr_text(token: Token, name: str) -> str:
    value = token.attrGet(name)
    return "" if value is None else str(value)


def process_inline_tokens(
    tokens: list[Token],
    *,
    external_links_new_tab: bool,
    check_links: bool,
    source_path: Path | None,
) -> tuple[str, ...]:
    """Mutate inline link/image tokens and return local-target warnings."""

    warnings: list[str] = []
    base_dir = source_path.parent if source_path is not None else None
    for token in tokens:
        if token.children:
            warnings.extend(
                process_inline_tokens(
                    token.children,
                    external_links_new_tab=external_links_new_tab,
                    check_links=check_links,
                    source_path=source_path,
                )
            )
        if token.type == "link_open":
            href = _attr_text(token, "href")
            if is_dangerous_url(href):
                token.attrSet("href", "")
                warnings.append("위험한 URL scheme이 제거되었습니다.")
                continue
            if check_links and base_dir is not None:
                warning = _local_target_warning(href, base_dir, "링크")
                if warning:
                    warnings.append(warning)
            token.attrSet("href", rewrite_markdown_link(href))
            if is_external_url(href):
                token.attrSet("rel", _merge_rel(_attr_text(token, "rel") or None))
                if external_links_new_tab:
                    token.attrSet("target", "_blank")
        elif token.type == "image":
            src = _attr_text(token, "src")
            if is_dangerous_url(src):
                token.attrSet("src", "")
                warnings.append("위험한 이미지 URL scheme이 제거되었습니다.")
            else:
                token.attrSet("loading", "lazy")
                if check_links and base_dir is not None:
                    warning = _local_target_warning(src, base_dir, "이미지")
                    if warning:
                        warnings.append(warning)
    return tuple(warnings)


def _local_target_warning(url: str, base_dir: Path, kind: str) -> str | None:
    parsed: SplitResult = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
        return None
    target = base_dir / unquote(parsed.path)
    if not target.exists():
        return f"존재하지 않는 로컬 {kind}: {parsed.path}"
    return None

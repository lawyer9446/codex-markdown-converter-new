"""Allow-list based HTML sanitization."""

from __future__ import annotations

import bleach

ALLOWED_TAGS = {
    "a",
    "abbr",
    "blockquote",
    "br",
    "code",
    "dd",
    "del",
    "details",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "input",
    "li",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}

ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "*": ["class", "id"],
    "a": ["href", "title", "rel", "target", "aria-label"],
    "blockquote": ["cite"],
    "img": ["src", "alt", "title", "loading", "width", "height"],
    "input": ["type", "disabled", "checked"],
    "nav": ["aria-label"],
    "ol": ["start"],
    "td": ["colspan", "rowspan", "align"],
    "th": ["colspan", "rowspan", "align", "scope"],
}


def sanitize_html(html: str) -> str:
    """Remove active content while preserving generated Markdown structures."""

    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
        strip_comments=True,
    )

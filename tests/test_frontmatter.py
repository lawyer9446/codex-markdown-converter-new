from __future__ import annotations

import pytest

from md_to_html import FrontMatterError, markdown_to_html


def test_no_front_matter() -> None:
    result = markdown_to_html("# 제목")
    assert dict(result.metadata) == {}


def test_empty_front_matter() -> None:
    result = markdown_to_html("---\n---\n# 제목")
    assert dict(result.metadata) == {}
    assert "<hr" not in result.html


@pytest.mark.parametrize(
    "source",
    [
        "---\ntitle: [unterminated\n---\nbody",
        "---\n- one\n- two\n---\nbody",
        "---\ntitle: value\nbody",
        "---\n!!python/object/apply:os.system ['echo unsafe']\n---\nbody",
    ],
)
def test_bad_or_unsafe_front_matter_is_rejected(source: str) -> None:
    with pytest.raises(FrontMatterError):
        markdown_to_html(source)


def test_unknown_metadata_is_ignored() -> None:
    result = markdown_to_html("---\ntitle: T\nunknown: secret\n---\nbody")
    assert dict(result.metadata) == {"title": "T"}

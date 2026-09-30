from __future__ import annotations

from pathlib import Path

import pytest

from md_to_html import (
    ConversionOptions,
    InputFileError,
    OutputFileError,
    convert_file,
    markdown_to_html,
)


def test_documented_sample_matches_expected_html() -> None:
    project_root = Path(__file__).parents[1]
    source = (project_root / "examples" / "sample.md").read_text(encoding="utf-8")
    expected = (project_root / "examples" / "sample.expected.html").read_text(encoding="utf-8")
    result = markdown_to_html(source, options=ConversionOptions(no_style=True))
    assert result.html == expected


def test_convert_file_writes_default_destination(tmp_path: Path) -> None:
    source = tmp_path / "문서.md"
    source.write_text("# 제목", encoding="utf-8")
    result = convert_file(source)
    assert result.output_path == tmp_path / "문서.html"
    assert result.output_path.read_text(encoding="utf-8") == result.html


def test_existing_output_is_protected(tmp_path: Path) -> None:
    source = tmp_path / "input.md"
    destination = tmp_path / "input.html"
    source.write_text("new", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")
    with pytest.raises(OutputFileError):
        convert_file(source)
    assert destination.read_text(encoding="utf-8") == "old"
    convert_file(source, overwrite=True)
    assert destination.read_text(encoding="utf-8") != "old"


@pytest.mark.parametrize("name", ["missing.md", "unsupported.txt"])
def test_invalid_input(name: str, tmp_path: Path) -> None:
    source = tmp_path / name
    if source.suffix == ".txt":
        source.write_text("text", encoding="utf-8")
    with pytest.raises(InputFileError):
        convert_file(source)


def test_bad_encoding_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "bad.md"
    source.write_bytes(b"\xff\xfe")
    with pytest.raises(InputFileError):
        convert_file(source, encoding="utf-8")


def test_nested_output_directory_is_created(tmp_path: Path) -> None:
    source = tmp_path / "input.md"
    source.write_text("body", encoding="utf-8")
    destination = tmp_path / "deep" / "nested" / "output.html"
    convert_file(source, destination)
    assert destination.is_file()

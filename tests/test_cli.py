from __future__ import annotations

from pathlib import Path

import pytest

from md_to_html.cli import main


def test_single_file_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "README.md"
    source.write_text("# 안녕하세요", encoding="utf-8")
    assert main([str(source), "--stdout", "--no-style"]) == 0
    captured = capsys.readouterr()
    assert "<!doctype html>" in captured.out
    assert "안녕하세요" in captured.out
    assert captured.err == ""


def test_stdin_to_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO("# 표준 입력"))
    assert main(["-", "--fragment"]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith('<h1 id="표준-입력">')


def test_directory_recursive_preserves_structure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "docs"
    output = tmp_path / "site"
    (source / "reference").mkdir(parents=True)
    (source / "index.md").write_text("# Index", encoding="utf-8")
    (source / "reference" / "api.markdown").write_text("# API", encoding="utf-8")
    assert main([str(source), "--output-dir", str(output), "--recursive"]) == 0
    assert (output / "index.html").is_file()
    assert (output / "reference" / "api.html").is_file()
    assert "성공 2" in capsys.readouterr().err


def test_directory_continues_after_existing_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "docs"
    output = tmp_path / "site"
    source.mkdir()
    output.mkdir()
    (source / "one.md").write_text("one", encoding="utf-8")
    (source / "two.md").write_text("two", encoding="utf-8")
    (output / "one.html").write_text("old", encoding="utf-8")
    assert main([str(source), "--output-dir", str(output)]) == 1
    assert (output / "one.html").read_text(encoding="utf-8") == "old"
    assert (output / "two.html").is_file()
    assert "실패 1" in capsys.readouterr().err


def test_output_tree_inside_input_is_not_rediscovered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "docs"
    output = source / "generated"
    output.mkdir(parents=True)
    (source / "index.md").write_text("# Index", encoding="utf-8")
    (output / "stale.md").write_text("# Do not process", encoding="utf-8")
    assert main([str(source), "--output-dir", str(output), "--recursive"]) == 0
    assert (output / "index.html").is_file()
    assert not (output / "generated" / "stale.html").exists()
    assert "성공 1" in capsys.readouterr().err


def test_missing_input_returns_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["definitely-missing.md"]) == 1
    assert "ERROR" in capsys.readouterr().err


def test_stdout_rejects_symlink_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    real = tmp_path / "real.md"
    link = tmp_path / "link.md"
    real.write_text("# real", encoding="utf-8")
    link.symlink_to(real)
    assert main([str(link), "--stdout"]) == 1
    assert "심볼릭 링크" in capsys.readouterr().err


@pytest.mark.parametrize(
    "arguments",
    [
        ["-", "--recursive"],
        ["-", "--output-dir", "out"],
    ],
)
def test_invalid_cli_combinations(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(arguments)
    assert raised.value.code == 2

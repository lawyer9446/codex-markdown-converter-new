"""Command-line interface for :mod:`md_to_html`."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from . import __version__
from .converter import _atomic_write, _read_markdown_file, convert_file, markdown_to_html
from .exceptions import InputFileError, MarkdownToHtmlError, OutputFileError
from .models import ConversionOptions, ConversionResult

LOGGER = logging.getLogger("md2html")
SUPPORTED_SUFFIXES = {".md", ".markdown"}


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="md2html",
        description="Markdown 파일이나 디렉터리를 안전한 HTML5로 변환합니다.",
    )
    parser.add_argument("input", metavar="INPUT", help="Markdown 파일, 디렉터리 또는 -")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("-o", "--output", type=Path, help="단일 출력 파일")
    destination.add_argument("--stdout", action="store_true", help="HTML을 표준 출력으로 보냄")
    parser.add_argument("--output-dir", type=Path, help="디렉터리 변환 출력 루트")
    parser.add_argument("--recursive", action="store_true", help="하위 디렉터리도 탐색")
    parser.add_argument("--overwrite", action="store_true", help="기존 출력 파일 덮어쓰기")
    parser.add_argument("--fragment", action="store_true", help="HTML 문서 대신 본문 조각 출력")
    parser.add_argument("--title", help="문서 제목 강제 지정")
    parser.add_argument("--lang", help="HTML lang 속성 지정")
    parser.add_argument("--toc", action="store_true", help="h2~h4 목차 생성")
    parser.add_argument(
        "--sanitize",
        action="store_true",
        default=True,
        help="허용 목록 기반 HTML 정화(항상 활성화)",
    )
    parser.add_argument(
        "--allow-raw-html",
        action="store_true",
        help="원시 HTML 파싱 허용(위험 요소 정화는 계속 적용)",
    )
    styles = parser.add_mutually_exclusive_group()
    styles.add_argument("--css", help="외부 CSS 경로 또는 URL 연결")
    styles.add_argument("--embed-css", type=Path, help="로컬 CSS 파일을 문서에 삽입")
    styles.add_argument("--no-style", action="store_true", help="기본 스타일 생략")
    parser.add_argument("--check-links", action="store_true", help="로컬 링크와 이미지 확인")
    parser.add_argument(
        "--external-links-new-tab",
        action="store_true",
        help="외부 링크를 새 탭에서 열기",
    )
    parser.add_argument("--encoding", default="utf-8", help="입출력 인코딩(기본: utf-8)")
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--verbose", action="store_true", help="상세 처리 로그")
    verbosity.add_argument("--quiet", action="store_true", help="오류 외 메시지 숨김")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _configure_logging(*, verbose: bool, quiet: bool) -> None:
    level = logging.DEBUG if verbose else logging.ERROR if quiet else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", stream=sys.stderr)


def _read_embedded_css(path: Path | None, encoding: str) -> str | None:
    if path is None:
        return None
    if path.is_symlink() or not path.is_file():
        raise InputFileError(f"CSS 파일을 읽을 수 없습니다: {path}")
    try:
        return path.read_text(encoding=encoding)
    except (OSError, UnicodeError, LookupError) as exc:
        raise InputFileError(f"CSS 파일을 읽을 수 없습니다: {path}: {exc}") from exc


def _options_from_args(args: argparse.Namespace) -> ConversionOptions:
    return ConversionOptions(
        standalone=not args.fragment,
        sanitize=True,
        toc=args.toc,
        lang=args.lang,
        title=args.title,
        allow_raw_html=args.allow_raw_html,
        external_links_new_tab=args.external_links_new_tab,
        check_links=args.check_links,
        css_href=args.css,
        embedded_css=_read_embedded_css(args.embed_css, args.encoding),
        no_style=args.no_style,
    )


def _validate_cli_shape(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    source_text: str = args.input
    if source_text == "-" and (args.output_dir is not None or args.recursive):
        parser.error("표준 입력에는 --output-dir 또는 --recursive를 사용할 수 없습니다.")
    source = Path(source_text) if source_text != "-" else None
    if source is not None and source.is_dir():
        if args.output_dir is None:
            parser.error("디렉터리 입력에는 --output-dir이 필요합니다.")
        if args.output is not None or args.stdout:
            parser.error("디렉터리 입력에는 --output 또는 --stdout을 사용할 수 없습니다.")
    elif args.output_dir is not None:
        parser.error("--output-dir은 디렉터리 입력에만 사용할 수 있습니다.")
    if args.recursive and (source is None or not source.is_dir()):
        parser.error("--recursive는 디렉터리 입력에만 사용할 수 있습니다.")


def _convert_text_input(
    markdown_text: str,
    *,
    options: ConversionOptions,
    output: Path | None,
    stdout: bool,
    overwrite: bool,
    encoding: str,
) -> ConversionResult:
    converted = markdown_to_html(markdown_text, options=options)
    if stdout or output is None:
        sys.stdout.write(converted.html)
        return converted
    _atomic_write(output, converted.html, overwrite=overwrite, encoding=encoding)
    return ConversionResult.create(
        html=converted.html,
        metadata=converted.metadata,
        warnings=converted.warnings,
        output_path=output,
    )


def _convert_single_file(
    source: Path,
    *,
    args: argparse.Namespace,
    options: ConversionOptions,
) -> ConversionResult:
    if args.stdout:
        text = _read_markdown_file(source, args.encoding)
        active = replace(options, source_path=source, fallback_title=source.stem)
        return _convert_text_input(
            text,
            options=active,
            output=None,
            stdout=True,
            overwrite=args.overwrite,
            encoding=args.encoding,
        )
    destination = args.output if args.output is not None else source.with_suffix(".html")
    return convert_file(
        source,
        destination,
        options=options,
        overwrite=args.overwrite,
        encoding=args.encoding,
    )


def _discover_markdown_files(
    source_dir: Path, recursive: bool, *, excluded_root: Path | None = None
) -> list[Path]:
    iterator = source_dir.rglob("*") if recursive else source_dir.glob("*")
    resolved_exclusion = excluded_root.resolve(strict=False) if excluded_root is not None else None
    return sorted(
        path
        for path in iterator
        if path.is_file()
        and not path.is_symlink()
        and path.suffix.casefold() in SUPPORTED_SUFFIXES
        and (
            resolved_exclusion is None
            or not path.resolve(strict=False).is_relative_to(resolved_exclusion)
        )
    )


def _safe_destination(source: Path, source_root: Path, output_root: Path) -> Path:
    relative = source.relative_to(source_root).with_suffix(".html")
    destination = output_root / relative
    resolved_root = output_root.resolve(strict=False)
    resolved_destination = destination.resolve(strict=False)
    if not resolved_destination.is_relative_to(resolved_root):
        raise OutputFileError(f"출력 디렉터리 밖의 경로는 사용할 수 없습니다: {destination}")
    return destination


def _convert_directory(
    source_dir: Path,
    *,
    output_dir: Path,
    args: argparse.Namespace,
    options: ConversionOptions,
) -> int:
    if source_dir.is_symlink():
        raise InputFileError(f"심볼릭 링크 입력 디렉터리는 처리하지 않습니다: {source_dir}")
    if output_dir.is_symlink():
        raise OutputFileError(f"심볼릭 링크 출력 디렉터리는 사용하지 않습니다: {output_dir}")
    files = _discover_markdown_files(source_dir, args.recursive, excluded_root=output_dir)
    success = warning_count = failure = 0
    for source in files:
        destination = _safe_destination(source, source_dir, output_dir)
        try:
            result = convert_file(
                source,
                destination,
                options=options,
                overwrite=args.overwrite,
                encoding=args.encoding,
            )
        except MarkdownToHtmlError as exc:
            failure += 1
            print(f"ERROR: {source}: {exc}", file=sys.stderr)
            continue
        success += 1
        warning_count += len(result.warnings)
        LOGGER.debug("변환 완료: %s -> %s", source, destination)
        for warning in result.warnings:
            LOGGER.warning("%s: %s", source, warning)
    if not args.quiet:
        print(
            f"완료: 성공 {success}, 경고 {warning_count}, 실패 {failure}",
            file=sys.stderr,
        )
    return 1 if failure else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(verbose=args.verbose, quiet=args.quiet)
    _validate_cli_shape(parser, args)
    try:
        options = _options_from_args(args)
        if args.input == "-":
            try:
                source_text = sys.stdin.read()
            except UnicodeError as exc:
                raise InputFileError(f"표준 입력을 읽을 수 없습니다: {exc}") from exc
            _convert_text_input(
                source_text,
                options=options,
                output=args.output,
                stdout=args.stdout or args.output is None,
                overwrite=args.overwrite,
                encoding=args.encoding,
            )
            return 0

        source = Path(args.input)
        if source.is_dir():
            return _convert_directory(
                source,
                output_dir=args.output_dir,
                args=args,
                options=options,
            )
        result = _convert_single_file(source, args=args, options=options)
        for warning in result.warnings:
            LOGGER.warning("%s", warning)
        if args.verbose and result.output_path is not None:
            LOGGER.debug("변환 완료: %s", result.output_path)
        return 0
    except MarkdownToHtmlError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

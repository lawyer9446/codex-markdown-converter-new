# Markdown HTML Transformer

`markdown-html-transformer`는 Markdown 문서와 디렉터리를 안전한 HTML5로 변환하는
Python 3.11+ 라이브러리이자 `md2html` 명령줄 도구입니다. GFM 표·작업 목록·취소선,
각주, Pygments 코드 강조, 목차, YAML 프런트매터, 상대 문서 링크 변환을 지원합니다.

신뢰할 수 없는 입력을 기본 전제로 삼습니다. 원시 HTML은 기본적으로 파싱하지 않으며,
파싱을 명시적으로 허용해도 Bleach 허용 목록 정화는 계속 적용됩니다.

## 설치

Python 3.11 이상이 필요합니다.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install .
```

개발 도구까지 설치하려면 다음을 실행합니다.

```bash
python -m pip install -e '.[dev]'
```

## 빠른 시작

입력 파일 옆에 같은 이름의 HTML을 생성합니다.

```bash
md2html README.md
```

출력 경로를 지정하거나 결과를 표준 출력으로 보낼 수 있습니다.

```bash
md2html README.md -o build/README.html
md2html README.md --stdout
python -m md_to_html README.md --stdout
```

기존 파일은 기본적으로 보호됩니다. 명시적으로 덮어쓰려면 `--overwrite`를 사용합니다.

```bash
md2html README.md -o build/README.html --overwrite
```

## 디렉터리 일괄 변환

디렉터리 입력에는 `--output-dir`이 필요합니다. `--recursive`를 지정하면 하위 디렉터리의
`.md`와 `.markdown` 파일도 찾으며, 입력의 상대 디렉터리 구조를 출력에 보존합니다.

```bash
md2html docs/ --output-dir site/
md2html docs/ --output-dir site/ --recursive --overwrite
```

일괄 변환은 파일 하나가 실패해도 나머지를 계속 처리합니다. 완료 후 성공·경고·실패
개수를 stderr에 출력하며, 하나라도 실패하면 종료 코드 `1`을 반환합니다.

## 표준 입력과 출력

입력 경로 `-`는 표준 입력을 뜻합니다. 출력 파일을 지정하지 않으면 HTML만 stdout으로
보내며 로그와 오류는 stderr로 보냅니다.

```bash
cat README.md | md2html -
cat README.md | md2html - -o README.html
md2html README.md --stdout
```

## 주요 CLI 옵션

```text
md2html INPUT
  -o, --output PATH            단일 출력 파일
  --output-dir PATH            디렉터리 변환 출력 루트
  --recursive                  하위 디렉터리 탐색
  --overwrite                  기존 출력 덮어쓰기
  --stdout                     결과를 stdout으로 출력
  --fragment                   완전한 문서 대신 HTML 조각 생성
  --title TEXT                 문서 제목 강제 지정
  --lang CODE                  <html lang> 값 강제 지정
  --toc                        h2~h4 목차 생성
  --math                       $...$ / $$...$$ 수식을 MathML로 변환
  --sanitize                   HTML 정화(호환성을 위한 명시 옵션, 항상 활성화)
  --allow-raw-html              원시 HTML 파싱 허용, 최종 정화는 유지
  --css PATH_OR_URL            외부 스타일시트 연결
  --embed-css PATH             로컬 CSS 내용을 <style>에 삽입
  --no-style                   기본 CSS 생략
  --check-links                로컬 링크와 이미지 존재 여부 확인
  --external-links-new-tab     HTTP(S) 외부 링크에 target="_blank" 추가
  --encoding NAME              입출력 인코딩, 기본 utf-8
  --verbose                    상세 로그
  --quiet                      오류 외 메시지 숨김
  --version                    버전 출력
```

`--css`, `--embed-css`, `--no-style`은 동시에 사용할 수 없습니다. `--verbose`와
`--quiet`, `--output`과 `--stdout`도 상호 배타적입니다. 전체 도움말은
`md2html --help`에서 확인할 수 있습니다.

## Python API

문자열 변환은 파일을 생성하거나 전역 로깅 설정을 변경하지 않습니다.

```python
from md_to_html import ConversionOptions, markdown_to_html

source = """
# 안녕하세요

이것은 **테스트**입니다.
"""

result = markdown_to_html(
    source,
    options=ConversionOptions(
        standalone=True,
        sanitize=True,
        toc=False,
        lang="ko",
    ),
)

print(result.html)
print(result.metadata)
print(result.warnings)
```

파일 API는 안전한 임시 파일에 먼저 쓴 뒤 원자적으로 출력 파일을 교체합니다.

```python
from pathlib import Path

from md_to_html import ConversionOptions, convert_file

result = convert_file(
    Path("docs/index.md"),
    Path("site/index.html"),
    options=ConversionOptions(toc=True, check_links=True),
    overwrite=False,
)
print(result.output_path)
```

`ConversionResult`에는 `html`, 읽기 전용 `metadata`, `warnings`, 선택적 `output_path`가
들어 있습니다. 예상 가능한 문제는 모두 `MarkdownToHtmlError` 하위 예외로 처리할 수
있습니다.

## YAML 프런트매터

문서 첫 줄의 `---` 블록에서 다음 네 필드를 읽습니다.

```yaml
---
title: 사용자 가이드
author: 홍길동
date: 2026-09-27
lang: ko
---
```

안전한 YAML 로더를 사용하며, 알 수 없는 필드는 결과 metadata에 포함하지 않습니다.
제목 우선순위는 CLI/API의 명시적 제목, 프런트매터 `title`, 첫 번째 `h1`, 입력 파일명,
`Document` 순입니다. 언어는 명시적 `lang`, 프런트매터 `lang`, `ko` 순입니다.

## Markdown 기능

다음 문법을 지원합니다.

- CommonMark 제목, 문단, 강조, 링크, 이미지, 인용문, 목록 및 fenced code block
- GFM 표, 작업 목록, 취소선 및 URL 자동 링크
- 각주
- 한글을 보존하는 고유 제목 ID
- 선택적 h2~h4 목차
- Pygments 코드 문법 강조

알 수 없는 코드 언어는 오류가 아니라 안전하게 이스케이프된 일반 코드 블록으로
처리됩니다. 목차의 링크와 실제 제목 ID는 같은 변환 과정에서 함께 생성됩니다. 중복 ID에는
`-2`, `-3` 접미사가 붙습니다.

## 수식

`--math`를 지정하면 LaTeX 형식의 인라인 수식 `$...$`과 블록 수식 `$$...$$`을
MathML로 변환합니다. 최신 Chrome, Edge, Firefox, Safari에서 외부 JavaScript나
CDN 없이 표시할 수 있습니다. 변환 후 HTML을 열 때 인터넷 연결이 필요하지 않습니다.

```markdown
에너지 관계식은 $E=mc^2$입니다.

$$
\frac{-b \pm \sqrt{b^2-4ac}}{2a}
$$
```

```bash
md2html examples/math.md --math -o build/math.html
```

Python API에서는 `ConversionOptions(math=True)`를 사용합니다.

```python
result = markdown_to_html(
    r"에너지 $E=mc^2$",
    options=ConversionOptions(math=True),
)
```

기본값은 수식 해석 비활성화입니다. 코드 블록과 인라인 코드 안의 달러 기호는
수식으로 처리하지 않으며, 일반 달러 기호는 `\$`로 이스케이프할 수 있습니다.
인라인 수식은 구분자 바로 안쪽에 공백을 넣지 않습니다. 가격과의 혼동을 줄이기 위해
여는 `$` 앞이나 닫는 `$` 뒤에 숫자가 바로 붙으면 인라인 수식으로 해석하지 않습니다.
블록 수식은 별도 문단에 작성하세요. fragment 모드에서도 MathML이 유지됩니다.

지원하는 LaTeX 문법은 `latex2mathml`의 변환 범위에 따릅니다. 전체 LaTeX 문서,
패키지 로딩, 사용자 매크로 및 수식 번호 자동 생성은 지원하지 않습니다.
변환기가 잘못된 수식으로 판단하면 API는 `MathConversionError`, CLI는 종료 코드
`1`을 반환합니다. 생성된 MathML에도 HTML 정화를 적용하므로 URL·인라인 스타일·
이벤트 핸들러를 이용하는 명령은 보존하지 않습니다.

## 링크와 이미지

다른 Markdown 문서를 가리키는 상대 링크만 `.html`로 바뀝니다.

```text
guide/install.md                -> guide/install.html
../intro.markdown#start         -> ../intro.html#start
https://example.com/manual.md   -> 변경 없음
#local-section                  -> 변경 없음
```

query와 fragment는 보존됩니다. HTTP(S) 외부 링크에는 항상
`rel="noopener noreferrer"`를 추가하고, 선택적으로 `target="_blank"`를 붙입니다.
이미지는 다운로드하거나 Base64로 바꾸지 않으며 `loading="lazy"`를 추가합니다.
`--check-links`는 입력 파일을 기준으로 존재하지 않는 로컬 대상에 경고만 발생시킵니다.

## CSS

완전한 문서에는 작은 반응형 기본 CSS가 포함됩니다. 다음 중 하나로 바꿀 수 있습니다.

```bash
md2html page.md --css /assets/site.css
md2html page.md --embed-css theme.css
md2html page.md --no-style
```

fragment 모드에서는 문서용 `<style>`과 `<link>`를 출력하지 않습니다. `--embed-css`는
사용자가 명시적으로 선택한 로컬 CSS 파일을 신뢰 입력으로 읽지만, `</style>`로 문서
구조를 탈출하는 문자열은 무력화합니다.

## 보안 정책

- 원시 HTML 파싱은 기본적으로 꺼져 있습니다.
- 최종 본문은 Bleach 태그·속성 허용 목록으로 항상 정화합니다.
- `script`, `iframe`, 이벤트 핸들러와 인라인 `style` 속성을 허용하지 않습니다.
- `javascript:`, `vbscript:`, `data:` URL을 허용하지 않습니다.
- 코드 블록 내용은 HTML로 실행되지 않습니다.
- 작업 목록 checkbox는 비활성화된 상태로 출력됩니다.
- 입력 및 출력 심볼릭 링크를 따라 작업 범위를 벗어나지 않습니다.
- 출력은 임시 파일을 거쳐 원자적으로 기록합니다.

`--allow-raw-html`은 신뢰된 문서에 필요한 제한적 HTML을 Markdown 파서가 읽게 하는
옵션입니다. 이 옵션을 사용해도 위험한 태그·속성·URL 정화는 비활성화되지 않습니다.
이 프로젝트는 정화를 완전히 끄는 CLI 옵션이나 API 모드를 제공하지 않습니다.

허용 목록은 표, 각주, 작업 목록, 목차와 Pygments가 생성하는 `class`/`id`를 보존합니다.
원격 콘텐츠의 안전성을 보장하거나 외부 링크의 대상 콘텐츠를 검사하지는 않습니다.

## 오류와 종료 코드

- `0`: 모든 요청 작업 성공
- `1`: 입력 읽기, 변환 또는 출력 쓰기 실패
- `2`: 잘못된 CLI 인자 또는 서로 충돌하는 옵션

예상 가능한 오류에는 기본적으로 traceback을 표시하지 않습니다. `--verbose`는 처리 경로와
추가 로그를 stderr에 출력하며, `--quiet`는 오류 외 메시지를 숨깁니다.

## 개발 및 검증

```bash
python -m pytest
ruff check .
ruff format --check .
mypy src
```

스모크 테스트:

```bash
md2html --help
md2html --version
md2html examples/sample.md --stdout
python -m md_to_html examples/sample.md --stdout
```

## 프로젝트 구조

```text
src/md_to_html/
├── cli.py          # CLI 인자, 배치 처리, 로그 및 종료 코드
├── converter.py    # Markdown 렌더링과 원자적 파일 변환
├── frontmatter.py  # 안전한 YAML 프런트매터
├── links.py        # URL 분류, 링크 변환 및 로컬 검사
├── models.py       # 공개 옵션과 결과 모델
├── security.py     # HTML 허용 목록 정화
└── styles.py       # 기본 CSS
```

## 알려진 제한사항

- Mermaid 렌더링은 포함하지 않습니다. 수식은 `--math`로 활성화하며 MathML 지원 브라우저가 필요합니다.
- 링크 검사는 로컬 대상의 존재 여부만 확인하며 HTTP 상태를 요청하지 않습니다.
- 한글 제목 ID는 읽기 쉬움을 위해 유니코드를 유지하므로, ASCII 전용 slug가 필요한 시스템은
  별도의 후처리가 필요합니다.
- 목차는 제목 수준을 반영한 중첩 목록을 생성하며 기본 범위는 h2~h4입니다.

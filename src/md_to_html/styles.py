"""Built-in styles for standalone documents."""

from pygments.formatters import HtmlFormatter

_LAYOUT_CSS = """
:root { color-scheme: light dark; }
body { max-width: 72rem; margin: 0 auto; padding: 2rem; font: 16px/1.65 system-ui, sans-serif; }
img { max-width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #8888; padding: .45rem .65rem; text-align: left; }
pre { overflow-x: auto; padding: 1rem; border-radius: .4rem; background: #8882; }
code { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.task-list { list-style: none; padding-left: 1.25rem; }
.table-of-contents { border-left: .25rem solid #8886; padding-left: 1rem; }
""".strip()

_PYGMENTS_CSS = HtmlFormatter().get_style_defs(".highlight")  # type: ignore[no-untyped-call]
DEFAULT_CSS = f"{_LAYOUT_CSS}\n{_PYGMENTS_CSS}"

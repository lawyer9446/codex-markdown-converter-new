"""Public exception hierarchy for :mod:`md_to_html`."""


class MarkdownToHtmlError(Exception):
    """Base class for errors users can handle without inspecting internals."""


class ConfigurationError(MarkdownToHtmlError):
    """Raised when conversion options are contradictory or unsafe."""


class FrontMatterError(MarkdownToHtmlError):
    """Raised when YAML front matter is malformed or has an invalid shape."""


class MathConversionError(MarkdownToHtmlError):
    """Raised when a LaTeX expression cannot be converted to MathML."""


class InputFileError(MarkdownToHtmlError):
    """Raised when an input file cannot be read or is unsupported."""


class OutputFileError(MarkdownToHtmlError):
    """Raised when an output file cannot be written safely."""

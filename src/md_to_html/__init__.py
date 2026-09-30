"""Safe Markdown-to-HTML conversion APIs."""

from .converter import convert_file, markdown_to_html
from .exceptions import (
    ConfigurationError,
    FrontMatterError,
    InputFileError,
    MarkdownToHtmlError,
    OutputFileError,
)
from .models import ConversionOptions, ConversionResult

__all__ = [
    "ConfigurationError",
    "ConversionOptions",
    "ConversionResult",
    "FrontMatterError",
    "InputFileError",
    "MarkdownToHtmlError",
    "OutputFileError",
    "convert_file",
    "markdown_to_html",
]

__version__ = "0.1.0"

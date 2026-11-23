"""ANSI colour policy shared by every renderer.

Colour is on for a TTY, off when NO_COLOR is set, off when --no-color is
passed, and forced on when FORCE_COLOR is set (the screenshot helper does
that).  Everything is plain ANSI SGR 8/16 colours so no terminal-specific
library is needed.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"


@dataclass(frozen=True)
class Theme:
    """Resolved colour policy."""

    enabled: bool

    def paint(self, text: str, *codes: str) -> str:
        if not self.enabled or not codes:
            return text
        return "".join(codes) + text + RESET

    def red(self, text: str) -> str:
        return self.paint(text, "\x1b[31m")

    def green(self, text: str) -> str:
        return self.paint(text, "\x1b[32m")

    def yellow(self, text: str) -> str:
        return self.paint(text, "\x1b[33m")

    def blue(self, text: str) -> str:
        return self.paint(text, "\x1b[34m")

    def magenta(self, text: str) -> str:
        return self.paint(text, "\x1b[35m")

    def cyan(self, text: str) -> str:
        return self.paint(text, "\x1b[36m")

    def grey(self, text: str) -> str:
        return self.paint(text, "\x1b[90m")

    def bold(self, text: str) -> str:
        return self.paint(text, BOLD)

    def heading(self, text: str) -> str:
        return self.paint(text, BOLD, "\x1b[36m")


def resolve_theme(no_color: bool = False, stream=None) -> Theme:
    """Decide whether to emit ANSI escapes for this process."""
    target = stream if stream is not None else sys.stdout
    if no_color:
        return Theme(False)
    # An explicit FORCE_COLOR wins over an inherited NO_COLOR: the screenshot
    # helpers set FORCE_COLOR on machines where NO_COLOR is exported globally.
    if os.environ.get("FORCE_COLOR"):
        return Theme(True)
    if os.environ.get("NO_COLOR"):
        return Theme(False)
    try:
        return Theme(bool(target.isatty()))
    except (AttributeError, ValueError):
        return Theme(False)


def colored_score(theme: Theme, total: float) -> str:
    """Colour a score by band: green >= 85, yellow >= 70, red below."""
    text = f"{total:.1f}"
    if total >= 85:
        return theme.green(text)
    if total >= 70:
        return theme.yellow(text)
    return theme.red(text)


def severity_tag(theme: Theme, severity: str) -> str:
    """Render a fixed-width severity tag."""
    label = {"error": "ERROR", "warning": "WARN ", "info": "INFO "}.get(severity, severity.upper())
    if severity == "error":
        return theme.red(theme.bold(label))
    if severity == "warning":
        return theme.yellow(label)
    return theme.grey(label)

"""Core data types shared by every prompt-atlas module.

Everything here is plain, frozen and deterministic: no I/O, no globals that
mutate.  A :class:`Document` is the single parsed representation that the
rules, the scorer, the differ and the reporters all consume.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field
from typing import Any

#: Axes used by the 0-100 score.
AXES: tuple[str, ...] = (
    "clarity",
    "specificity",
    "structure",
    "constraints",
    "examples",
    "robustness",
)

AXIS_WEIGHTS: dict[str, float] = {
    "clarity": 0.20,
    "specificity": 0.20,
    "structure": 0.15,
    "constraints": 0.20,
    "examples": 0.10,
    "robustness": 0.15,
}

SEVERITY_RANK: dict[str, int] = {"info": 0, "warning": 1, "error": 2}

GRADE_TABLE: tuple[tuple[int, str], ...] = (
    (95, "A+"),
    (90, "A"),
    (85, "A-"),
    (80, "B+"),
    (75, "B"),
    (70, "B-"),
    (65, "C+"),
    (60, "C"),
    (55, "D+"),
    (50, "D"),
    (0, "F"),
)

HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
VAR_USE_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}")



class PromptAtlasError(Exception):
    """Base class for expected, user-facing errors (never a raw traceback)."""


class FrontmatterError(PromptAtlasError):
    """Raised when the YAML-lite frontmatter cannot be parsed."""

    def __init__(self, message: str, line: int) -> None:
        super().__init__(f"{message} (frontmatter line {line})")
        self.message = message
        self.line = line


@dataclass(frozen=True)
class Issue:
    """One rule violation."""

    rule: str
    severity: str
    message: str
    line: int
    hint: str
    axis: str
    deduction: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "line": self.line,
            "message": self.message,
            "hint": self.hint,
            "axis": self.axis,
            "deduction": round(self.deduction, 2),
        }


@dataclass(frozen=True)
class Section:
    """A markdown heading and every line below it, up to the next heading."""

    title: str
    level: int
    start_line: int
    end_line: int
    lines: tuple[str, ...] = field(default_factory=tuple)

    @property
    def body(self) -> str:
        return "\n".join(self.lines)

    @property
    def key(self) -> str:
        """Normalised identity used by the section-aware differ."""
        return re.sub(r"[^a-z0-9]+", " ", self.title.lower()).strip()

    @property
    def label(self) -> str:
        if self.level == 0:
            return "(preamble)"
        return "#" * self.level + " " + self.title


@dataclass(frozen=True)
class ScoreResult:
    """Weighted 0-100 quality score with per-axis detail and top fixes."""

    total: float
    grade: str
    axes: dict[str, float]
    fixes: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": round(self.total, 1),
            "grade": self.grade,
            "axes": {name: round(value, 1) for name, value in self.axes.items()},
            "fixes": [dict(fix) for fix in self.fixes],
        }


@dataclass(frozen=True)
class LintResult:
    """Everything the CLI needs to know about one linted prompt."""

    path: str
    document: Document
    issues: tuple[Issue, ...]
    score: ScoreResult

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.document.meta.get("name"),
            "version": self.document.meta.get("version"),
            "tokens": self.document.token_count,
            "sections": len(self.document.sections),
            "instructions": self.document.instruction_count,
            "score": self.score.as_dict(),
            "findings": [issue.as_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class Document:
    """A parsed prompt: frontmatter, markdown sections and derived metrics."""

    path: str
    text: str
    lines: tuple[str, ...]
    meta: dict[str, Any] = field(default_factory=dict)
    fm_line_count: int = 0
    sections: tuple[Section, ...] = field(default_factory=tuple)
    token_count: int = 0
    instruction_count: int = 0
    lower_body: str = ""
    newlines: tuple[int, ...] = ()
    word_set: frozenset[str] = frozenset()
    vars_used: tuple[str, ...] = field(default_factory=tuple)
    vars_declared: tuple[str, ...] = field(default_factory=tuple)

    @property
    def body(self) -> str:
        return "\n".join(self.lines)

    def line_index_for_offset(self, offset: int) -> int:
        """0-based index into lines for a character offset into the body."""
        return bisect.bisect_left(self.newlines, offset)

    def line_for_offset(self, offset: int) -> int:
        """1-based file line for a character offset into the body."""
        return self.fm_line_count + self.line_index_for_offset(offset) + 1

    def line_text(self, line: int) -> str:
        if 1 <= line <= len(self.lines):
            return self.lines[line - 1]
        return ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.meta.get("name"),
            "version": self.meta.get("version"),
            "model": self.meta.get("model"),
            "tags": list(self.meta.get("tags") or []),
            "vars_declared": list(self.vars_declared),
            "vars_used": list(self.vars_used),
            "tokens": self.token_count,
            "instructions": self.instruction_count,
            "sections": [
                {"title": s.title, "level": s.level, "start": s.start_line, "end": s.end_line}
                for s in self.sections
            ],
        }

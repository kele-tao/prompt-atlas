"""Public library API.

CI users should not have to shell out, so everything the CLI does is
available as a function returning plain dataclasses::

    from prompt_atlas import lint_file

    result = lint_file("prompts/support.md")
    if result.score.total < 80:
        raise SystemExit("prompt quality gate failed")
"""

from __future__ import annotations

from .api_impl import (
    diff_files,
    diff_text,
    lint_document,
    lint_file,
    lint_text,
    render_html,
    render_json,
    render_markdown,
)
from .differ import DiffResult
from .document import load_document
from .model import AXES, AXIS_WEIGHTS, Document, Issue, LintResult, PromptAtlasError, ScoreResult
from .rules import RULE_NAMES, run_rules
from .scorer import score_document

__version__ = "1.0.0"

__all__ = [
    "AXES",
    "AXIS_WEIGHTS",
    "DiffResult",
    "Document",
    "Issue",
    "LintResult",
    "PromptAtlasError",
    "RULE_NAMES",
    "ScoreResult",
    "__version__",
    "diff_files",
    "diff_text",
    "lint_document",
    "lint_file",
    "lint_text",
    "load_document",
    "render_html",
    "render_json",
    "render_markdown",
    "run_rules",
    "score_document",
]

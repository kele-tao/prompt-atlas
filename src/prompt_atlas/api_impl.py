"""Implementation behind the public :mod:`prompt_atlas` functions.

Kept separate so ``__init__`` stays a readable, stable public surface and
import cycles stay impossible.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterable

from .differ import DiffResult, diff_documents
from .document import load_document, parse_document
from .htmlreport import render_html_report
from .model import Document, LintResult
from .reporters import results_to_json, results_to_markdown
from .rules import run_rules
from .scorer import score_document


def lint_document(document: Document) -> LintResult:
    """Lint a parsed document and score it."""
    issues = run_rules(document)
    score = score_document(document, issues)
    return LintResult(path=document.path, document=document, issues=tuple(issues), score=score)


def lint_text(text: str, path: str = "<text>") -> LintResult:
    """Lint raw prompt source. Never touches the filesystem."""
    return lint_document(parse_document(text, path))


def lint_file(path: pathlib.Path | str) -> LintResult:
    """Load and lint one prompt file."""
    return lint_document(load_document(path))


def diff_text(old_text: str, new_text: str, old_path: str = "<old>", new_path: str = "<new>") -> DiffResult:
    """Diff two prompt strings."""
    old = parse_document(old_text, old_path)
    new = parse_document(new_text, new_path)
    old_result = lint_document(old)
    new_result = lint_document(new)
    return diff_documents(old, new, score_delta=new_result.score.total - old_result.score.total)


def diff_files(old_path: pathlib.Path | str, new_path: pathlib.Path | str) -> DiffResult:
    """Diff two prompt files."""
    old = load_document(old_path)
    new = load_document(new_path)
    old_result = lint_document(old)
    new_result = lint_document(new)
    return diff_documents(old, new, score_delta=new_result.score.total - old_result.score.total)


def render_html(results: Iterable[LintResult], version: str = "1.0.0", title: str = "prompt-atlas report") -> str:
    """Render the self-contained HTML report for a set of results."""
    return render_html_report(results, version, title)


def render_markdown(results: Iterable[LintResult], version: str = "1.0.0") -> str:
    """Render the Markdown report for a set of results."""
    return results_to_markdown(list(results), version)


def render_json(results: Iterable[LintResult], version: str = "1.0.0") -> str:
    """Render the JSON report for a set of results."""
    return results_to_json(results, version)


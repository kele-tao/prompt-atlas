"""Command line interface for prompt-atlas.

Exit codes (documented in the README and enforced by tests):

* 0 - clean: no findings at or above the failure threshold, score gate passed
* 1 - findings: the quality gate failed
* 2 - usage error: bad arguments, unreadable file, malformed frontmatter
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from collections.abc import Sequence

from . import __version__
from .api_impl import diff_files, lint_document
from .document import discover_prompts, load_document
from .htmlreport import render_html_report
from .model import SEVERITY_RANK, PromptAtlasError
from .render import render_diff, render_lint, render_score
from .reporters import diff_to_json, results_to_json, results_to_markdown
from .scorer import potential_gain
from .theme import Theme, resolve_theme

PROG = "prompt-atlas"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Lint, score and diff LLM prompts like source code.",
        epilog="Exit codes: 0 clean, 1 findings at or above --fail-on, 2 usage error.",
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    sub = parser.add_subparsers(dest="command", metavar="command")

    lint = sub.add_parser("lint", help="lint a prompt file or a directory of prompts")
    lint.add_argument("path", help="file or directory to lint")
    lint.add_argument("--fail-on", choices=["info", "warning", "error", "none"], default="error",
                      help="lowest severity that fails the run (default: error)")
    lint.add_argument("--min-score", type=float, default=None,
                      help="fail when the score is below this value")
    lint.add_argument("--json", action="store_true", help="emit JSON instead of a card")
    lint.add_argument("--max-findings", type=int, default=40, help="findings to print per prompt")
    lint.add_argument("--no-color", action="store_true", help="disable ANSI colour")

    score = sub.add_parser("score", help="score one prompt and show the highest-impact fixes")
    score.add_argument("path", help="prompt file to score")
    score.add_argument("--json", action="store_true", help="emit JSON")
    score.add_argument("--min-score", type=float, default=None, help="exit 1 below this score")
    score.add_argument("--no-color", action="store_true", help="disable ANSI colour")

    diff = sub.add_parser("diff", help="section-aware diff of two prompt versions")
    diff.add_argument("old", help="baseline prompt")
    diff.add_argument("new", help="candidate prompt")
    diff.add_argument("--json", action="store_true", help="emit JSON")
    diff.add_argument("--format", choices=["md", "json", "text"], default="text")
    diff.add_argument("--no-color", action="store_true", help="disable ANSI colour")

    report = sub.add_parser("report", help="render a report for a directory of prompts")
    report.add_argument("path", help="directory (or single file) to analyse")
    report.add_argument("--out", default="report.html", help="output file (default: report.html)")
    report.add_argument("--format", choices=["md", "json", "html"], default="html")
    report.add_argument("--title", default="prompt-atlas report", help="HTML report title")
    report.add_argument("--min-score", type=float, default=None, help="fail below this mean score")
    return parser


def _theme(args: argparse.Namespace) -> Theme:
    return resolve_theme(no_color=bool(getattr(args, "no_color", False)))


def _exit_for_issues(results, fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = SEVERITY_RANK[fail_on]
    for result in results:
        for issue in result.issues:
            if SEVERITY_RANK[issue.severity] >= threshold:
                return 1
    return 0


def _cmd_lint(args: argparse.Namespace) -> int:
    theme = _theme(args)
    paths = discover_prompts(args.path)
    if not paths:
        raise PromptAtlasError(f"no prompt files (.md/.txt/.prompt) under {args.path}")
    results = []
    for path in paths:
        try:
            results.append(lint_document(load_document(path)))
        except PromptAtlasError as exc:
            raise PromptAtlasError(f"{path}: {exc}") from exc
    if args.json:
        print(results_to_json(results, __version__))
    else:
        for index, result in enumerate(results):
            if index:
                print("")
            print(render_lint(result, theme, max_findings=args.max_findings))
        if len(results) > 1:
            mean = sum(r.score.total for r in results) / len(results)
            worst = min(results, key=lambda item: item.score.total)
            print(
                theme.heading("Summary")
                + f"  {len(results)} prompts, mean score {mean:.1f}, worst "
                + f"{worst.document.meta.get('name') or worst.path} at {worst.score.total:.1f}"
            )
    code = _exit_for_issues(results, args.fail_on)
    if args.min_score is not None:
        below = [r for r in results if r.score.total < args.min_score]
        if below and not args.json:
            for result in below:
                name = result.document.meta.get("name") or result.path
                print(theme.red(
                    f"score gate failed: {name} scored {result.score.total:.1f} "
                    f"< {args.min_score:.1f}"
                ))
        if below:
            code = 1
    return code


def _cmd_score(args: argparse.Namespace) -> int:
    theme = _theme(args)
    result = lint_document(load_document(args.path))
    if args.json:
        print(results_to_json([result], __version__))
    else:
        print(render_score(result, theme))
        gain = potential_gain(result.score)
        if gain:
            print(theme.grey(f"  Fixing the top 3 findings is worth up to {gain:.1f} points."))
    if args.min_score is not None and result.score.total < args.min_score:
        if not args.json:
            print(theme.red(f"score gate failed: {result.score.total:.1f} < {args.min_score:.1f}"))
        return 1
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    theme = _theme(args)
    result = diff_files(args.old, args.new)
    if args.json or args.format == "json":
        print(diff_to_json(result, __version__))
        return 0
    if args.format == "md":
        print(render_diff_markdown(result))
        return 0
    print(render_diff(result, theme))
    return 0


def render_diff_markdown(result) -> str:
    """Markdown rendering of a diff, for pasting into a pull request."""
    lines = [
        "## prompt-atlas diff",
        "",
        f"`{result.old_path}` -> `{result.new_path}`",
        "",
        f"**Verdict: {result.verdict}** (risk: {result.risk}) - {result.risk_note}",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Sections added | {len(result.sections_added)} |",
        f"| Sections removed | {len(result.sections_removed)} |",
        f"| Sections modified | {len(result.sections_modified)} |",
        f"| Lines added | {result.added} |",
        f"| Lines removed | {result.removed} |",
        f"| Token delta | {result.token_delta:+d} |",
        f"| Score delta | {result.score_delta:+.1f} |",
    ]
    if result.constraints_added:
        lines.extend(["", "### Constraints added", ""])
        lines.extend(f"- {text}" for text in result.constraints_added)
    if result.constraints_removed:
        lines.extend(["", "### Constraints removed", ""])
        lines.extend(f"- {text}" for text in result.constraints_removed)
    if result.polarity_flips:
        lines.extend(["", "### Polarity flips", ""])
        for flip in result.polarity_flips:
            lines.append(f"- [{flip.section}] `{flip.old_text}` -> `{flip.new_text}`")
    return "\n".join(lines)


def _cmd_report(args: argparse.Namespace) -> int:
    paths = discover_prompts(args.path)
    if not paths:
        raise PromptAtlasError(f"no prompt files (.md/.txt/.prompt) under {args.path}")
    results = [lint_document(load_document(path)) for path in paths]
    out = pathlib.Path(args.out)
    if args.format == "json":
        body = results_to_json(results, __version__)
    elif args.format == "md":
        body = results_to_markdown(results, __version__)
    else:
        body = render_html_report(results, __version__, args.title)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
    except OSError as exc:
        raise PromptAtlasError(f"cannot write {out}: {exc.strerror or exc}") from exc
    mean = sum(r.score.total for r in results) / len(results)
    print(f"wrote {out} ({len(body.encode('utf-8'))} bytes) from {len(results)} prompts, mean score {mean:.1f}")
    if args.min_score is not None and mean < args.min_score:
        print(f"score gate failed: mean {mean:.1f} < {args.min_score:.1f}")
        return 1
    return 0


COMMANDS = {"lint": _cmd_lint, "score": _cmd_score, "diff": _cmd_diff, "report": _cmd_report}


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: parse arguments, dispatch, translate errors to exit codes."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    handler = COMMANDS[args.command]
    try:
        return handler(args)
    except PromptAtlasError as exc:
        print(f"{PROG}: error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
    except KeyboardInterrupt:
        print(f"{PROG}: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())

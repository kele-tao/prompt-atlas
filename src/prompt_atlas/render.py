"""Terminal rendering: lint cards, score cards and diff reviews.

Everything returns a plain string so tests can assert on it with colour
disabled.  Layout is fixed-width and deterministic: no locale, no clock, no
terminal-width probing.
"""

from __future__ import annotations

from .differ import DiffResult
from .model import AXES, LintResult
from .theme import Theme, colored_score, severity_tag

BAR_WIDTH = 24
FILL = "#"
EMPTY = "."

AXIS_HINTS = {
    "clarity": "unambiguous language",
    "specificity": "measurable requirements",
    "structure": "sections and ordering",
    "constraints": "hard limits and scope",
    "examples": "worked input/output pairs",
    "robustness": "variables, PII, failure modes",
}


def bar(value: float, width: int = BAR_WIDTH) -> str:
    """A deterministic ASCII meter for a 0-100 value."""
    filled = max(0, min(width, round(value / 100.0 * width)))
    return FILL * filled + EMPTY * (width - filled)


def plural(count: int, singular: str, plural_form: str = "") -> str:
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural_form or singular + chr(115)}"


def _header(theme: Theme, result: LintResult) -> list[str]:
    document = result.document
    meta = document.meta
    name = str(meta.get("name") or result.path)
    version = meta.get("version")
    model = meta.get("model")
    facts = [f"{document.token_count} tokens", plural(len(document.sections), "section")]
    if version:
        facts.insert(0, f"v{version}")
    if model:
        facts.append(str(model))
    return [
        theme.heading("prompt-atlas"),
        "  " + theme.bold(name) + theme.grey("  " + " | ".join(facts)),
        "",
    ]


def render_findings(result: LintResult, theme: Theme, limit: int = 40) -> list[str]:
    issues = result.issues
    lines: list[str] = []
    if not issues:
        lines.append("  " + theme.green("No findings. Nothing to fix."))
        return lines
    counts = {
        "error": sum(1 for i in issues if i.severity == "error"),
        "warning": sum(1 for i in issues if i.severity == "warning"),
        "info": sum(1 for i in issues if i.severity == "info"),
    }
    summary = ", ".join(
        f"{count} {name}" + ("" if count == 1 else "s")
        for name, count in counts.items()
        if count
    )
    lines.append(theme.heading(f"  Findings  ({summary})"))
    for issue in issues[:limit]:
        tag = severity_tag(theme, issue.severity)
        line = f"    {tag}  {theme.cyan(issue.rule)}  L{issue.line:<4} {issue.message}"
        lines.append(line)
        lines.append(theme.grey("           -> " + issue.hint))
    if len(issues) > limit:
        lines.append(theme.grey(f"    ... {len(issues) - limit} more findings (raise --max-findings)"))
    return lines


def render_score_block(result: LintResult, theme: Theme) -> list[str]:
    score = result.score
    lines = [
        "",
        "  "
        + theme.heading("Score  ")
        + theme.bold(colored_score(theme, score.total))
        + theme.grey(" / 100  ")
        + theme.bold(score.grade),
    ]
    for axis in AXES:
        value = score.axes[axis]
        lines.append(
            f"    {axis:<12} {theme.cyan(bar(value))} {colored_score(theme, value):>5}  "
            + theme.grey(AXIS_HINTS[axis])
        )
    return lines


def render_fixes(result: LintResult, theme: Theme) -> list[str]:
    fixes = result.score.fixes
    if not fixes:
        return []
    lines = ["", "  " + theme.heading("Top fixes")]
    for index, fix in enumerate(fixes, start=1):
        lines.append(
            f"    {index}. {theme.cyan(str(fix['rule']))}  +{fix['impact']:.1f} pts  {fix['message']}"
        )
        lines.append(theme.grey("       " + str(fix["fix"])))
    return lines


def render_lint(result: LintResult, theme: Theme, max_findings: int = 40) -> str:
    """Render the full lint card: header, findings, score and top fixes."""
    lines: list[str] = []
    lines.extend(_header(theme, result))
    lines.extend(render_findings(result, theme, max_findings))
    lines.extend(render_score_block(result, theme))
    lines.extend(render_fixes(result, theme))
    lines.append("")
    return "\n".join(lines)


def render_score(result: LintResult, theme: Theme) -> str:
    """Render only the score card, used by the score subcommand."""
    lines: list[str] = []
    lines.extend(_header(theme, result))
    lines.extend(render_score_block(result, theme))
    lines.extend(render_fixes(result, theme))
    lines.append("")
    return "\n".join(lines)


def _verdict_color(theme: Theme, verdict: str) -> str:
    if verdict == "tightening":
        return theme.yellow(verdict.upper())
    if verdict == "loosening":
        return theme.red(verdict.upper())
    if verdict == "mixed":
        return theme.magenta(verdict.upper())
    return theme.green(verdict.upper())


def render_diff(result: DiffResult, theme: Theme, limit: int = 30) -> str:
    """Render a section-aware diff review card."""
    lines: list[str] = [
        theme.heading("prompt-atlas diff"),
        "  " + theme.bold(result.old_path) + theme.grey("  ->  ") + theme.bold(result.new_path),
        "",
        "  " + theme.heading("Verdict  ")
        + _verdict_color(theme, result.verdict)
        + theme.grey(f"   risk: {result.risk}"),
        "  " + theme.grey(result.risk_note),
        "",
        "  " + theme.heading("Changes"),
        f"    sections  {theme.green('+' + str(len(result.sections_added)))} added  "
        f"{theme.red('-' + str(len(result.sections_removed)))} removed  "
        f"{theme.yellow('~' + str(len(result.sections_modified)))} modified",
        f"    lines     {theme.green('+' + str(result.added))} added  "
        f"{theme.red('-' + str(result.removed))} removed",
        f"    tokens    {result.token_delta:+d}   score {result.score_delta:+.1f}",
    ]
    if result.constraints_added or result.constraints_removed:
        lines.append("")
        lines.append("  " + theme.heading("Constraint delta"))
        for text in result.constraints_added[:limit]:
            lines.append("    " + theme.green("+ ") + text)
        for text in result.constraints_removed[:limit]:
            lines.append("    " + theme.red("- ") + text)
    if result.polarity_flips:
        lines.append("")
        lines.append("  " + theme.heading("Polarity flips"))
        for flip in result.polarity_flips:
            lines.append("    " + theme.magenta("! ") + theme.grey(f"[{flip.section}]"))
            lines.append("      " + theme.red("- " + flip.old_text[:96]))
            lines.append("      " + theme.green("+ " + flip.new_text[:96]))
            lines.append(theme.grey("      shared objects: " + ", ".join(flip.objects)))
    if result.changes:
        lines.append("")
        lines.append("  " + theme.heading("Line changes"))
        for change in result.changes[:limit]:
            marker = {"added": theme.green("+"), "removed": theme.red("-")}.get(change.kind, " ")
            where = theme.grey(f"[{change.section[:28]}]")
            lines.append(f"    {marker} {where} {change.text[:96]}")
        if len(result.changes) > limit:
            lines.append(theme.grey(f"    ... {len(result.changes) - limit} more changes"))
    lines.append("")
    return "\n".join(lines)

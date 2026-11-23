"""The deterministic 0-100 prompt quality score.

Design: every axis starts at 100 and loses points only for findings that map
to that axis.  Each rule may deduct at most once per document per rule code
(a repeated issue never double-charges), and the result is a weighted mean of
the six axes.  There is no randomness and no model call, so the same bytes
always produce the same score - which is what makes it usable in CI.
"""

from __future__ import annotations

from .model import AXES, AXIS_WEIGHTS, GRADE_TABLE, Document, Issue, ScoreResult

MAX_PER_RULE = 25.0


def letter_grade(total: float) -> str:
    """Map a 0-100 score to a letter grade (A+ at 95 and above)."""
    for threshold, grade in GRADE_TABLE:
        if total >= threshold:
            return grade
    return "F"


def _axis_scores(issues: tuple[Issue, ...] | list[Issue]) -> dict[str, float]:
    per_rule: dict[tuple[str, str], float] = {}
    for issue in issues:
        key = (issue.axis, issue.rule)
        per_rule[key] = min(MAX_PER_RULE, per_rule.get(key, 0.0) + issue.deduction)
    axes: dict[str, float] = {}
    for axis in AXES:
        deduction = sum(value for (name, _), value in per_rule.items() if name == axis)
        axes[axis] = max(0.0, 100.0 - deduction)
    return axes


def _top_fixes(issues: tuple[Issue, ...] | list[Issue], limit: int = 3) -> tuple[dict, ...]:
    scored: list[tuple[float, Issue]] = []
    seen: set[str] = set()
    for issue in issues:
        if issue.rule in seen:
            continue
        seen.add(issue.rule)
        impact = issue.deduction * AXIS_WEIGHTS[issue.axis]
        scored.append((impact, issue))
    scored.sort(key=lambda item: (-item[0], item[1].rule))
    fixes: list[dict] = []
    for impact, issue in scored[:limit]:
        fixes.append(
            {
                "rule": issue.rule,
                "line": issue.line,
                "axis": issue.axis,
                "impact": round(impact, 1),
                "message": issue.message,
                "fix": issue.hint,
            }
        )
    return tuple(fixes)


def score_document(document: Document, issues: list[Issue]) -> ScoreResult:
    """Compute the weighted score for a parsed document plus its findings."""
    axes = _axis_scores(issues)
    total = sum(axes[axis] * AXIS_WEIGHTS[axis] for axis in AXES)
    return ScoreResult(
        total=round(total, 1),
        grade=letter_grade(total),
        axes={axis: round(axes[axis], 1) for axis in AXES},
        fixes=_top_fixes(issues),
    )


def potential_gain(result: ScoreResult) -> float:
    """Points the top fixes are worth, used by the before/after workflow."""
    return round(sum(float(fix["impact"]) for fix in result.fixes), 1)

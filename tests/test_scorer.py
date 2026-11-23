"""Scoring: determinism, axis mapping, grades and top-fix selection."""

from __future__ import annotations

import json

from prompt_atlas import lint_text
from prompt_atlas.model import AXES, AXIS_WEIGHTS
from prompt_atlas.scorer import letter_grade, potential_gain, score_document


def test_weights_sum_to_one():
    assert abs(sum(AXIS_WEIGHTS.values()) - 1.0) < 1e-9
    assert set(AXIS_WEIGHTS) == set(AXES)


def test_grade_boundaries():
    assert letter_grade(100) == "A+"
    assert letter_grade(95) == "A+"
    assert letter_grade(94.9) == "A"
    assert letter_grade(80) == "B+"
    assert letter_grade(50) == "D"
    assert letter_grade(0) == "F"


def test_score_is_deterministic():
    text = "# Task\nHandle the thing, some of it, etc. Be concise.\nExplain in detail."
    first = lint_text(text).score.as_dict()
    second = lint_text(text).score.as_dict()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_perfect_prompt_scores_100():
    text = (
        "---\nname: perfect\n---\n"
        "You are a refunds analyst. You are precise.\n\n"
        "## Input\n- `order` (string): the order id.\n\n"
        "## Rules\n- You must answer within 120 words.\n- Never invent facts.\n\n"
        "## Output format\nReturn only JSON: {\"ok\": true}.\n\n"
        "## Failure modes\nIf the order is missing, say so and stop.\n\n"
        "## Example\nInput: #1\nOutput: {\"ok\": true}\n\n"
    )
    result = lint_text(text)
    assert result.issues == ()
    assert result.score.total == 100.0
    assert result.score.grade == "A+"


def test_axes_track_their_findings():
    text = "# Task\nHandle the thing carefully.\nContact dana@example.com."
    result = lint_text(text)
    assert result.score.axes["robustness"] < 100
    assert result.score.axes["clarity"] < 100


def test_axis_never_goes_below_zero():
    text = "\n".join("Contact dana%d@example.com and use card 4242 4242 4242 4242." % i for i in range(20))
    result = lint_text(text)
    assert all(value >= 0.0 for value in result.score.axes.values())


def test_top_fixes_are_three_or_fewer_and_unique():
    result = lint_text("# Task\nHandle the thing, some of it, etc. Be concise.\nExplain in detail.")
    fixes = result.score.fixes
    assert 1 <= len(fixes) <= 3
    assert len({fix["rule"] for fix in fixes}) == len(fixes)
    assert set(fixes[0]) == {"rule", "line", "axis", "impact", "message", "fix"}


def test_top_fixes_are_ordered_by_impact():
    result = lint_text("# Task\nHandle the thing, some of it, etc. Be concise.\nExplain in detail.")
    impacts = [fix["impact"] for fix in result.score.fixes]
    assert impacts == sorted(impacts, reverse=True)


def test_clean_prompt_has_no_fixes():
    result = lint_text("You are a helper.\nYou must answer in JSON.\nExample: {}")
    result2 = score_document(result.document, [])
    assert result2.total == 100.0
    assert potential_gain(result2) == 0.0


def test_potential_gain_is_positive_when_findings_exist():
    result = lint_text("# Task\nHandle the thing, some of it, etc.")
    assert potential_gain(result.score) > 0

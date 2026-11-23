"""Diff: section awareness, constraint tracking, polarity flips, verdicts."""

from __future__ import annotations

from prompt_atlas import diff_files, diff_text

BASE = "You are a helper.\n\n## Rules\n- You must answer in English.\n"


def test_identical_prompts_are_neutral():
    result = diff_text(BASE, BASE)
    assert result.verdict == "neutral"
    assert result.changes == ()
    assert result.added == 0 and result.removed == 0


def test_added_constraint_is_tightening():
    new = BASE + "- You must never exceed 100 words.\n"
    result = diff_text(BASE, new)
    assert result.verdict == "tightening"
    assert result.risk == "medium"
    assert any("100 words" in text for text in result.constraints_added)


def test_removed_constraint_is_loosening():
    new = "You are a helper.\n\n## Rules\n- Answer politely.\n"
    result = diff_text(BASE, new)
    assert result.verdict == "loosening"
    assert result.constraints_removed


def test_polarity_flip_is_high_risk():
    old = "You are a helper.\n\n## Rules\n- You may issue a refund without approval.\n"
    new = "You are a helper.\n\n## Rules\n- You must never issue a refund without approval.\n"
    result = diff_text(old, new)
    assert result.polarity_flips
    assert result.verdict == "mixed"
    assert result.risk == "high"
    assert "re-run" in result.risk_note


def test_sections_added_and_removed_are_reported():
    old = "## A\nalpha\n"
    new = "## B\nbeta\n"
    result = diff_text(old, new)
    assert result.sections_added == ("B",)
    assert result.sections_removed == ("A",)


def test_token_delta_is_signed():
    result = diff_text(BASE, BASE + "extra words here to grow the prompt\n")
    assert result.token_delta > 0


def test_diff_serialises_to_json_safe_dict():
    result = diff_text(BASE, BASE + "- You must cite the policy.\n")
    payload = result.as_dict()
    assert payload["verdict"] == "tightening"
    assert isinstance(payload["changes"], list)
    assert "risk_note" in payload


def test_example_pair_flip_is_detected():
    from prompt_atlas.document import discover_prompts

    root = __import__("pathlib").Path(__file__).parents[1] / "examples"
    paths = {p.name: p for p in discover_prompts(root)}
    result = diff_files(paths["support-agent-v1.md"], paths["support-agent.md"])
    assert result.verdict == "mixed"
    assert result.risk == "high"
    assert result.polarity_flips
    assert result.score_delta > 20


def test_diff_of_missing_file_reports_cleanly(tmp_path):
    from prompt_atlas.model import PromptAtlasError

    try:
        diff_files(tmp_path / "nope.md", tmp_path / "nope2.md")
    except PromptAtlasError as exc:
        assert "no such file" in str(exc)
    else:
        raise AssertionError("expected PromptAtlasError")

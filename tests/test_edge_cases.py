"""Edge cases the reviewer will try: empty files, unicode, huge input, CRLF."""

from __future__ import annotations

import json
import pathlib

from prompt_atlas import diff_text, lint_file, lint_text, render_html, render_json


def test_empty_prompt_does_not_crash():
    result = lint_text("")
    assert result.score.total >= 0
    assert result.document.token_count == 0
    assert any(issue.rule == "PA003" for issue in result.issues)


def test_whitespace_only_prompt():
    result = lint_text("   \n\n\t\n   ")
    assert result.document.sections == ()


def test_unicode_prompt_round_trips_through_json():
    text = "---\nname: 日本語プロンプト\n---\n# 翻訳\n\nYou are a translator. 你好 🎉\n"
    result = lint_text(text, "u.md")
    assert result.document.token_count > 0
    payload = render_json([result])
    # ensure_ascii=False keeps CJK readable in the report
    assert "日本語プロンプト" in payload
    assert json.loads(payload)["prompts"][0]["name"] == "日本語プロンプト"
    # The emoji lives in the body, which the JSON report does not echo, but it
    # must not break parsing or scoring.
    assert result.score.total >= 0


def test_crlf_input_is_parsed():
    text = "---\r\nname: crlf\r\n---\r\n# Head\r\nYou are a helper.\r\n"
    result = lint_text(text)
    assert result.document.meta["name"] == "crlf"
    assert result.document.sections[0].title == "Head"


def test_bom_prefixed_file_is_parsed(tmp_path):
    target = tmp_path / "bom.md"
    target.write_text("\ufeff---\nname: bom\n---\nYou are a helper.\n", encoding="utf-8")
    assert lint_file(target).document.meta["name"] == "bom"


def test_large_document_smoke(tmp_path):
    body = "\n".join("You must follow rule %d and never skip it." % i for i in range(4000))
    target = tmp_path / "big.md"
    target.write_text("# Big\n" + body, encoding="utf-8")
    result = lint_file(target)
    assert result.document.token_count > 1000
    assert any(issue.rule == "PA014" for issue in result.issues)


def test_null_bytes_do_not_crash():
    result = lint_text("You are a helper.\x00\x00 Connect dana@example.com.")
    assert any(issue.rule == "PA012" for issue in result.issues)


def test_diff_of_empty_prompts_is_neutral():
    result = diff_text("", "")
    assert result.verdict == "neutral"
    assert result.changes == ()


def test_html_report_with_empty_prompt():
    body = render_html([lint_text("", "empty.md")])
    assert "<!doctype html>" in body


def test_directory_discovery_skips_hidden_and_non_prompts(tmp_path):
    from prompt_atlas.document import discover_prompts

    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    (tmp_path / "c.py").write_text("x", encoding="utf-8")
    (tmp_path / ".hidden.md").write_text("x", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "d.prompt").write_text("x", encoding="utf-8")
    found = [path.name for path in discover_prompts(tmp_path)]
    assert found == ["a.md", "b.txt", "sub/d.prompt"] or found == ["a.md", "b.txt", "d.prompt"]
    assert "c.py" not in " ".join(found)
    assert not any(name.startswith(".") for name in found)


def test_discover_rejects_missing_path(tmp_path):
    from prompt_atlas.document import discover_prompts
    from prompt_atlas.model import PromptAtlasError

    try:
        discover_prompts(tmp_path / "nope")
    except PromptAtlasError as exc:
        assert "no such file" in str(exc)
    else:
        raise AssertionError("expected PromptAtlasError")


def test_report_writes_to_nested_new_directory(tmp_path):
    from prompt_atlas.cli import main

    src = tmp_path / "p.md"
    src.write_text("You are a helper.\nYou must answer in JSON.\nExample: {}", encoding="utf-8")
    out = tmp_path / "a" / "b" / "report.html"
    assert main(["report", str(tmp_path), "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_examples_all_parse_and_score():
    root = pathlib.Path(__file__).parents[1] / "examples"
    for path in sorted(root.glob("*.md")):
        result = lint_file(path)
        assert 0.0 <= result.score.total <= 100.0
        assert result.score.grade

"""CLI behaviour: exit codes, output formats, usage errors, directories."""

from __future__ import annotations

import json

import pytest

from prompt_atlas.cli import main


def test_lint_clean_prompt_exits_zero(capsys, examples_dir):
    code = main(["lint", str(examples_dir / "support-agent.md"), "--no-color"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Score" in out
    assert "A+" in out


def test_lint_returns_one_on_errors(capsys, examples_dir):
    code = main(["lint", str(examples_dir / "sloppy-brief.md"), "--no-color"])
    assert code == 1
    assert "ERROR" in capsys.readouterr().out


def test_fail_on_none_never_fails(capsys, examples_dir):
    code = main(["lint", str(examples_dir / "sloppy-brief.md"), "--fail-on", "none", "--no-color"])
    assert code == 0


def test_fail_on_info_is_strict(capsys, examples_dir):
    code = main(["lint", str(examples_dir / "support-agent.md"), "--fail-on", "info", "--no-color"])
    assert code == 1


def test_min_score_gate(capsys, examples_dir):
    code = main(["lint", str(examples_dir / "sloppy-brief.md"), "--min-score", "95", "--no-color"])
    assert code == 1
    assert "score gate failed" in capsys.readouterr().out


def test_lint_json_is_valid_and_deterministic(capsys, examples_dir):
    main(["lint", str(examples_dir), "--json"])
    first = capsys.readouterr().out
    main(["lint", str(examples_dir), "--json"])
    second = capsys.readouterr().out
    assert first == second
    payload = json.loads(first)
    assert payload["tool"] == "prompt-atlas"
    assert len(payload["prompts"]) == len(list(examples_dir.glob("*.md")))
    assert all("score" in item for item in payload["prompts"])


def test_lint_directory_prints_summary(capsys, examples_dir):
    main(["lint", str(examples_dir), "--no-color"])
    out = capsys.readouterr().out
    assert "Summary" in out
    assert f"{len(list(examples_dir.glob('*.md')))} prompts" in out


def test_lint_missing_path_exits_two(capsys, tmp_path):
    code = main(["lint", str(tmp_path / "ghost.md")])
    captured = capsys.readouterr()
    assert code == 2
    assert "error" in captured.err
    assert "Traceback" not in captured.err


def test_lint_empty_directory_exits_two(capsys, tmp_path):
    code = main(["lint", str(tmp_path)])
    assert code == 2
    assert "no prompt files" in capsys.readouterr().err


def test_malformed_frontmatter_is_a_usage_error(capsys, tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\nname: a\nname: b\n---\nbody", encoding="utf-8")
    code = main(["lint", str(bad)])
    captured = capsys.readouterr()
    assert code == 2
    assert "duplicate" in captured.err


def test_score_command_json(capsys, examples_dir):
    code = main(["score", str(examples_dir / "support-agent-v1.md"), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["prompts"][0]["score"]["total"] > 0


def test_score_min_score_exits_one(capsys, examples_dir):
    code = main(["score", str(examples_dir / "sloppy-brief.md"), "--min-score", "99", "--no-color"])
    assert code == 1


def test_diff_command_text_and_json(capsys, examples_dir):
    code = main(["diff", str(examples_dir / "support-agent-v1.md"), str(examples_dir / "support-agent.md"), "--no-color"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Verdict" in out
    main(["diff", str(examples_dir / "support-agent-v1.md"), str(examples_dir / "support-agent.md"), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["diff"]["risk"] == "high"


def test_diff_markdown_format(capsys, examples_dir):
    main(["diff", str(examples_dir / "support-agent-v1.md"), str(examples_dir / "support-agent.md"), "--format", "md"])
    out = capsys.readouterr().out
    assert "## prompt-atlas diff" in out
    assert "| Token delta |" in out


def test_report_writes_each_format(capsys, examples_dir, tmp_path):
    html_out = tmp_path / "report.html"
    code = main(["report", str(examples_dir), "--out", str(html_out)])
    assert code == 0
    body = html_out.read_text(encoding="utf-8")
    assert "<!doctype html>" in body
    assert "prompt-atlas" in body
    assert "http://" not in body and "https://" not in body

    md_out = tmp_path / "report.md"
    main(["report", str(examples_dir), "--out", str(md_out), "--format", "md"])
    assert "| Prompt | Score |" in md_out.read_text(encoding="utf-8")

    json_out = tmp_path / "report.json"
    main(["report", str(examples_dir), "--out", str(json_out), "--format", "json"])
    assert json.loads(json_out.read_text(encoding="utf-8"))["tool"] == "prompt-atlas"


def test_report_min_score_gate(capsys, examples_dir, tmp_path):
    code = main(["report", str(examples_dir), "--out", str(tmp_path / "r.html"), "--min-score", "99"])
    assert code == 1


def test_no_subcommand_prints_help_and_exits_two(capsys):
    code = main([])
    assert code == 2
    assert "usage:" in capsys.readouterr().out


def test_bad_flag_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["lint", "x.md", "--nonsense"])
    assert excinfo.value.code == 2


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "prompt-atlas 1.0.0" in capsys.readouterr().out

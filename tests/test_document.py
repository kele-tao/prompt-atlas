"""Document parsing: sections, token estimate, instruction counting, vars."""

from __future__ import annotations

import pytest

from prompt_atlas.document import (
    count_instructions,
    estimate_tokens,
    load_document,
    parse_document,
    split_sections,
)
from prompt_atlas.model import PromptAtlasError


def test_sections_split_on_headings():
    doc = parse_document("# A\nbody a\n## B\nbody b\n")
    titles = [section.title for section in doc.sections]
    assert titles == ["A", "B"]
    assert doc.sections[0].body.strip() == "body a"
    assert doc.sections[1].start_line == 4


def test_preamble_becomes_level_zero_section():
    sections = split_sections(("intro text", "# Head", "x"))
    assert sections[0].level == 0
    assert sections[0].label == "(preamble)"
    assert sections[1].title == "Head"


def test_section_keys_normalise_punctuation():
    doc = parse_document("## Output format!\nx")
    assert doc.sections[0].key == "output format"


def test_token_estimate_counts_cjk_characters():
    ascii_tokens = estimate_tokens("hello world this is a sentence")
    cjk_tokens = estimate_tokens("日本語のプロンプトを書いてください")
    assert 3 <= ascii_tokens <= 12
    assert cjk_tokens == 17
    assert estimate_tokens("") == 0


def test_instruction_count_counts_bullets_and_modals_not_prose():
    lines = ("Some ordinary prose with no instruction.", "- first rule", "- second rule")
    assert count_instructions(lines) == 2
    modal = ("You must answer in JSON.", "Never guess the order id.")
    assert count_instructions(modal) == 2


def test_vars_used_and_declared_are_extracted():
    text = "---\nvars: [a, b]\n---\nHello {{a}} and {{ c }}"
    doc = parse_document(text)
    assert doc.vars_declared == ("a", "b")
    assert doc.vars_used == ("a", "c")
    assert doc.fm_line_count == 3


def test_unicode_body_is_preserved():
    doc = parse_document("# 日本語\nこんにちは 🎉")
    assert "こんにちは" in doc.body
    assert "🎉" in doc.body
    assert doc.token_count > 0


def test_load_document_reports_missing_file():
    with pytest.raises(PromptAtlasError) as excinfo:
        load_document("does/not/exist.md")
    assert "no such file" in str(excinfo.value)


def test_load_document_reports_bad_utf8(tmp_path):
    target = tmp_path / "bad.md"
    target.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(PromptAtlasError) as excinfo:
        load_document(target)
    assert "UTF-8" in str(excinfo.value)


def test_load_document_rejects_directory(tmp_path):
    with pytest.raises(PromptAtlasError) as excinfo:
        load_document(tmp_path)
    assert "directory" in str(excinfo.value)


def test_document_dict_round_trip():
    doc = parse_document("---\nname: n\nversion: 3\nmodel: gpt-4o\n---\n# S\ntext")
    payload = doc.as_dict()
    assert payload["name"] == "n"
    assert payload["version"] == 3
    assert payload["model"] == "gpt-4o"
    assert payload["sections"][0]["title"] == "S"

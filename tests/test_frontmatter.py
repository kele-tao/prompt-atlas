"""Frontmatter parser: the YAML-lite subset, and its error messages."""

from __future__ import annotations

import pytest

from prompt_atlas.frontmatter import parse_frontmatter_lines, parse_scalar, split_frontmatter
from prompt_atlas.model import FrontmatterError


def test_scalars_are_typed():
    assert parse_scalar("42") == 42
    assert parse_scalar("3.5") == 3.5
    assert parse_scalar("true") is True
    assert parse_scalar("false") is False
    assert parse_scalar("null") is None
    assert parse_scalar("plain text") == "plain text"


def test_inline_list_with_quotes_and_comments():
    assert parse_scalar("[a, b, c] # note") == ["a", "b", "c"]
    assert parse_scalar("[]") == []
    assert parse_scalar("'quoted # not a comment'") == "quoted # not a comment"


def test_block_list_and_nested_mapping():
    meta = parse_frontmatter_lines(["tags:", "  - support", "  - refunds"])
    assert meta == {"tags": ["support", "refunds"]}
    nested = parse_frontmatter_lines(["vars:", "  tone: friendly", "  user: string"])
    assert nested == {"vars": {"tone": "friendly", "user": "string"}}


def test_split_frontmatter_returns_body_and_line_count():
    text = "---\nname: demo\nversion: 2\n---\n\n# Title\nbody"
    meta, count, body = split_frontmatter(text)
    assert meta == {"name": "demo", "version": 2}
    assert count == 5
    assert body.startswith("# Title")


def test_no_frontmatter_is_not_an_error():
    meta, count, body = split_frontmatter("# Just a heading\ntext")
    assert meta == {}
    assert count == 0
    assert body.startswith("# Just a heading")


def test_unclosed_frontmatter_reports_line_one():
    with pytest.raises(FrontmatterError) as excinfo:
        split_frontmatter("---\nname: demo")
    assert excinfo.value.line == 1
    assert "never closed" in str(excinfo.value)


def test_duplicate_key_is_rejected_with_line_number():
    with pytest.raises(FrontmatterError) as excinfo:
        parse_frontmatter_lines(["name: a", "name: b"])
    assert excinfo.value.line == 2
    assert "duplicate" in str(excinfo.value)


def test_bad_syntax_points_at_the_offending_line():
    with pytest.raises(FrontmatterError) as excinfo:
        parse_frontmatter_lines(["name: a", "this is not yaml"])
    assert excinfo.value.line == 2


def test_tab_indentation_is_rejected():
    with pytest.raises(FrontmatterError) as excinfo:
        parse_frontmatter_lines(["tag:", "\t- x"])
    assert "tabs" in str(excinfo.value)


def test_bom_is_stripped():
    meta, _, body = split_frontmatter("\ufeff---\nname: bom\n---\nhi")
    assert meta == {"name": "bom"}
    assert body.strip() == "hi"

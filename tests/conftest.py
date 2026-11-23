"""Shared fixtures for the prompt-atlas test suite."""

from __future__ import annotations

import pathlib

import pytest

from prompt_atlas import lint_text

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@pytest.fixture()
def examples_dir() -> pathlib.Path:
    return EXAMPLES


@pytest.fixture()
def good_prompt() -> str:
    return (EXAMPLES / "support-agent.md").read_text(encoding="utf-8")


@pytest.fixture()
def sloppy_prompt() -> str:
    return (EXAMPLES / "sloppy-brief.md").read_text(encoding="utf-8")


@pytest.fixture()
def lint():
    return lint_text

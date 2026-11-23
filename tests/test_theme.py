"""Colour policy: TTY detection, NO_COLOR, FORCE_COLOR, and the paint helpers."""

from __future__ import annotations

import io

from prompt_atlas.theme import Theme, colored_score, resolve_theme, severity_tag


class FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_theme_disabled_by_default_on_a_pipe():
    assert resolve_theme(stream=io.StringIO()).enabled is False


def test_theme_enabled_on_a_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    assert resolve_theme(stream=FakeTTY()).enabled is True


def test_no_color_flag_wins():
    assert resolve_theme(no_color=True, stream=FakeTTY()).enabled is False


def test_no_color_env(monkeypatch):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    assert resolve_theme(stream=FakeTTY()).enabled is False


def test_force_color_env_overrides_no_color(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    assert resolve_theme(stream=io.StringIO()).enabled is True
    assert resolve_theme(no_color=True, stream=io.StringIO()).enabled is False


def test_paint_is_a_no_op_when_disabled():
    theme = Theme(False)
    assert theme.red("x") == "x"
    assert theme.bold("x") == "x"


def test_paint_wraps_when_enabled():
    theme = Theme(True)
    assert theme.red("x").startswith("\x1b[31m")
    assert theme.red("x").endswith("\x1b[0m")
    assert "x" in theme.red("x")


def test_colored_score_bands():
    theme = Theme(True)
    assert "\x1b[32m" in colored_score(theme, 90)
    assert "\x1b[33m" in colored_score(theme, 75)
    assert "\x1b[31m" in colored_score(theme, 20)


def test_severity_tag_renders_labels():
    theme = Theme(True)
    assert "ERROR" in severity_tag(theme, "error")
    assert "WARN" in severity_tag(theme, "warning")
    assert "INFO" in severity_tag(theme, "info")

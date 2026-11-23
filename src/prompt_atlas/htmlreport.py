"""Self-contained HTML report: inline CSS, inline SVG, no JavaScript, no CDN.

The report is a single file so it can be attached to a PR or opened offline.
Every value printed comes from a real lint run.
"""

from __future__ import annotations

import html as html_mod
from collections.abc import Iterable

from .model import AXES, LintResult
from .reporters import summary_row

GRADE_COLORS = {
    "A+": "#16a34a",
    "A": "#16a34a",
    "A-": "#22c55e",
    "B+": "#84cc16",
    "B": "#eab308",
    "B-": "#f59e0b",
    "C+": "#f97316",
    "C": "#ef4444",
    "D+": "#dc2626",
    "D": "#b91c1c",
    "F": "#991b1b",
}
SEVERITY_COLORS = {"error": "#ef4444", "warning": "#f59e0b", "info": "#64748b"}

CSS = """
:root {
  --bg: #0b0f17;
  --panel: #121826;
  --panel-2: #0f1522;
  --line: #1f2937;
  --text: #e5e7eb;
  --muted: #8b9bb4;
  --accent: #22d3ee;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 40px 32px 64px;
  background: radial-gradient(1200px 600px at 20% -10%, #16243a 0%, var(--bg) 60%);
  color: var(--text);
  font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
.wrap { max-width: 1120px; margin: 0 auto; }
h1 { font-size: 30px; margin: 0 0 4px; letter-spacing: -0.02em; }
.sub { color: var(--muted); margin: 0 0 28px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
.card {
  background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
  border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px;
}
.card h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); margin: 0 0 12px; font-weight: 600; }
.big { font-size: 40px; font-weight: 700; line-height: 1; }
.grade { font-size: 15px; color: var(--muted); margin-top: 6px; }
table { width: 100%; border-collapse: collapse; margin-top: 8px; }
th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--line);
  font-size: 14px; vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.06em; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.mono { font-family: ui-monospace, SFMono-Regular, Consolas, "Cascadia Mono", monospace; }
.bar { display: flex; align-items: center; gap: 10px; margin: 7px 0; }
.bar span.name { width: 96px; color: var(--muted); font-size: 13px; }
.bar .track { flex: 1; height: 10px; background: #1b2334; border-radius: 99px; overflow: hidden; }
.bar .fill { height: 100%; border-radius: 99px; }
.bar b { width: 44px; text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; }
.pill { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11px;
  font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.rule { color: var(--accent); font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; }
.hint { color: var(--muted); font-size: 13px; }
.section { margin-top: 28px; }
footer { color: var(--muted); font-size: 12.5px; margin-top: 40px; }
"""


def esc(value: object) -> str:
    return html_mod.escape(str(value))


def score_color(value: float) -> str:
    if value >= 85:
        return "#22c55e"
    if value >= 70:
        return "#eab308"
    if value >= 50:
        return "#f97316"
    return "#ef4444"


def axis_bars(result: LintResult) -> str:
    rows: list[str] = []
    for axis in AXES:
        value = result.score.axes[axis]
        rows.append(
            f'<div class="bar"><span class="name">{esc(axis)}</span>'
            f'<span class="track"><span class="fill" style="width:{value:.1f}%;'
            f'background:{score_color(value)}"></span></span>'
            f'<b>{value:.1f}</b></div>'
        )
    return "".join(rows)


def sparkline(values: list[float], width: int = 220, height: int = 34) -> str:
    """Deterministic inline SVG sparkline - no JavaScript, works offline."""
    if not values:
        return ""
    step = width / max(1, len(values) - 1)
    points = []
    for index, value in enumerate(values):
        x = index * step
        y = height - (max(0.0, min(100.0, value)) / 100.0) * height
        points.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="score distribution">'
        f'<polyline fill="none" stroke="#22d3ee" stroke-width="2" points="{" ".join(points)}"/>'
        "</svg>"
    )


def render_html_report(results: Iterable[LintResult], version: str, title: str = "prompt-atlas report") -> str:
    """Render the full standalone HTML report."""
    items = list(results)
    rows = [summary_row(item) for item in items]
    total = len(items)
    mean = round(sum(row["score"] for row in rows) / total, 1) if total else 0.0
    errors = sum(row["errors"] for row in rows)
    warnings = sum(row["warnings"] for row in rows)
    clean = sum(1 for row in rows if row["findings"] == 0)
    best = max(items, key=lambda item: item.score.total) if items else None
    worst = min(items, key=lambda item: item.score.total) if items else None
    limit = 60

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append('<html lang="en"><head><meta charset="utf-8">')
    parts.append(f"<title>{esc(title)}</title>")
    parts.append(f"<style>{CSS}</style></head><body><div class=\"wrap\">")
    parts.append("<h1>prompt-atlas</h1>")
    parts.append(
        '<p class="sub">Static prompt lint report - '
        f"{total} prompts, {errors} errors, {warnings} warnings, {clean} clean.</p>"
    )
    parts.append('<div class="grid">')
    parts.append(
        '<div class="card"><h2>Mean score</h2>'
        f'<div class="big" style="color:{score_color(mean)}">{mean:.1f}</div>'
        f'<div class="grade">over {total} prompt{"s" if total != 1 else ""}</div></div>'
    )
    if best is not None and worst is not None:
        parts.append(
            '<div class="card"><h2>Best prompt</h2>'
            f'<div class="big" style="font-size:22px">{esc(best.document.meta.get("name") or best.path)}</div>'
            f'<div class="grade">{best.score.total:.1f} - grade {best.score.grade}</div></div>'
        )
        parts.append(
            '<div class="card"><h2>Needs work</h2>'
            f'<div class="big" style="font-size:22px">{esc(worst.document.meta.get("name") or worst.path)}</div>'
            f'<div class="grade">{worst.score.total:.1f} - grade {worst.score.grade}</div></div>'
        )
    parts.append(
        '<div class="card"><h2>Score spread</h2>'
        + sparkline([row["score"] for row in rows])
        + '<div class="grade">one point per prompt, left to right</div></div>'
    )
    parts.append("</div>")

    parts.append('<div class="card section"><h2>Prompt scores</h2><table>')
    parts.append(
        '<tr><th>Prompt</th><th class="num">Score</th><th>Grade</th>'
        '<th class="num">Tokens</th><th class="num">Err</th><th class="num">Warn</th>'
        '<th class="num">Info</th></tr>'
    )
    for row in sorted(rows, key=lambda item: (-item["score"], item["name"])):
        parts.append(
            f'<tr><td class="mono">{esc(row["name"])}</td>'
            f'<td class="num" style="color:{score_color(row["score"])}">{row["score"]:.1f}</td>'
            f'<td><span class="pill" style="background:{GRADE_COLORS.get(row["grade"], "#475569")}22;'
            f'color:{GRADE_COLORS.get(row["grade"], "#475569")}">{esc(row["grade"])}</span></td>'
            f'<td class="num">{row["tokens"]}</td>'
            f'<td class="num">{row["errors"]}</td>'
            f'<td class="num">{row["warnings"]}</td>'
            f'<td class="num">{row["infos"]}</td></tr>'
        )
    parts.append("</table></div>")

    parts.append('<div class="section"><h2>Axis breakdown</h2><div class="grid">')
    for result in items:
        name = result.document.meta.get("name") or result.path
        parts.append(
            f'<div class="card"><h2>{esc(name)} - {result.score.total:.1f} ({esc(result.score.grade)})</h2>'
            + axis_bars(result)
            + "</div>"
        )
    parts.append("</div></div>")

    parts.append('<div class="card section"><h2>Findings</h2><table>')
    parts.append(
        '<tr><th>Prompt</th><th>Rule</th><th>Severity</th><th class="num">Line</th>'
        '<th>Message</th><th>Suggested fix</th></tr>'
    )
    shown = 0
    for result in items:
        name = result.document.meta.get("name") or result.path
        for issue in result.issues:
            if shown >= limit:
                break
            color = SEVERITY_COLORS[issue.severity]
            parts.append(
                f'<tr><td class="mono">{esc(name)}</td>'
                f'<td class="rule">{esc(issue.rule)}</td>'
                f'<td><span class="pill" style="background:{color}22;color:{color}">'
                f'{esc(issue.severity)}</span></td>'
                f'<td class="num">{issue.line}</td>'
                f"<td>{esc(issue.message)}</td>"
                f'<td class="hint">{esc(issue.hint)}</td></tr>'
            )
            shown += 1
    parts.append("</table></div>")
    parts.append(
        f'<footer>Generated by prompt-atlas <b>{esc(version)}</b>. '
        "Scores are deterministic: the same bytes always produce the same number.</footer>"
    )
    parts.append("</div></body></html>")
    return "\n".join(parts)

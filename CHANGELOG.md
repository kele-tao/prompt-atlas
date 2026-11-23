# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-23

### Added

- `lint` command with 20 rules (PA001-PA020), `--fail-on` severity gate,
  `--min-score` gate, `--json` output and directory mode with a summary line.
- `score` command with the weighted six-axis 0-100 score, letter grade and the
  three highest-impact fixes with their point value.
- `diff` command with section-aware line changes, constraint deltas, polarity-
  flip detection and a tightening / loosening / mixed verdict plus risk note.
- `report` command emitting self-contained HTML, Markdown or JSON.
- Zero-dependency YAML-lite frontmatter parser with line-accurate errors and
  declared-vs-used variable validation.
- Library API (`lint_text`, `lint_file`, `diff_text`, `diff_files`,
  `render_html`, `render_markdown`, `render_json`).
- Benchmark harness (`python benchmarks/run.py`) that writes `results.json` and
  `RESULTS.md`, which is where the README performance table comes from.

### Notes

- Exit codes: 0 clean, 1 gate failed, 2 usage error.
- Python 3.10+, no runtime dependencies.

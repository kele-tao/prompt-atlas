"""Regenerate the README benchmark block from benchmarks/RESULTS.md.

Run after benchmarks/run.py::

    python benchmarks/run.py && python benchmarks/sync_readme.py

This keeps the README table byte-identical to the committed results file, so
the numbers in the README can never drift from the ones the script produced.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKER = "<!-- BENCH-TABLE -->"


def render_table() -> str:
    results = (ROOT / "benchmarks" / "RESULTS.md").read_text(encoding="utf-8")
    lines = results.splitlines()
    body = [line for line in lines if line.startswith("|") or line.startswith("## ")]
    return "\n".join(body).strip() + "\n"


def main() -> int:
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if MARKER not in readme:
        print("README has no " + MARKER + " marker", file=sys.stderr)
        return 2
    start = readme.index(MARKER) + len(MARKER)
    end = readme.index("\n## ", start)
    updated = readme[:start] + "\n\n" + render_table() + readme[end:]
    readme_path.write_text(updated, encoding="utf-8")
    print("synced " + str(len(render_table().splitlines())) + " benchmark lines into README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Contributing

Thanks for taking a look. This is a small, deliberately boring codebase:
stdlib only, deterministic output, no network, no async.

## Development setup

```bash
git clone https://github.com/kele-tao/prompt-atlas.git
cd prompt-atlas
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
ruff check .
```

## The rules for adding a rule

1. **Pick the next free code.** Codes are `PA001`-style and are never reused or
   renumbered; a removed rule leaves a hole, because people write CI policies
   against them.
2. **One file, one function.** Add `rule_<name>(document) -> list[Issue]` to
   `src/prompt_atlas/rules.py`, then register it in `RULES`. It must be a pure
   function of the `Document` - no I/O, no global state, no randomness.
3. **Map it to an axis.** `clarity`, `specificity`, `structure`, `constraints`,
   `examples` or `robustness`. The axis decides what the finding costs the score.
4. **Write the fix hint as an instruction**, not a complaint. "Replace 'etc' with
   a countable rule" beats "vague quantifier found".
5. **Add two tests**: one that triggers the rule, one that proves it does not
   fire on reasonable prose. False positives are the whole risk of a linter.
6. **No new dependencies.** If it needs a library, it needs a better design.

## Determinism

Two runs on the same bytes must produce byte-identical output. If your rule
iterates a `set`, sort it first. `tests/test_scorer.py` and
`tests/test_cli.py` assert this.

## Pull requests

- Keep the diff focused; unrelated reformatting will be asked to split.
- Update `CHANGELOG.md` under an "Unreleased" heading.
- `pytest -q` and `ruff check .` must both be green; CI runs them on 3.10, 3.11
  and 3.12.
- If you change a rule's severity or deduction, say so in the PR description:
  it moves people's scores.

## Reporting bugs

Open an issue with the prompt that triggers it (redact anything private), the
command you ran, the output you got and the output you expected.

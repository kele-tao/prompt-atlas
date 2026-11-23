# Roadmap

What shipped in v1.0, what was deliberately cut, and what comes next.

## Shipped in v1.0

- 20 static rules (PA001-PA020) with stable codes, severities and one-line fixes.
- Deterministic 0-100 score across six weighted axes, letter grade and the top 3
  highest-impact fixes, computed from the same findings the rules emit.
- Section-aware diff with constraint tracking, polarity-flip detection and a
  tightening / loosening / mixed verdict plus a risk note.
- YAML-lite frontmatter parser (no PyYAML) that validates declared variables
  against the placeholders actually used in the body.
- Terminal cards, Markdown, JSON and a self-contained HTML report (inline CSS,
  inline SVG, no JavaScript, no network).
- Library API: `from prompt_atlas import lint_file, diff_files, render_json`.

## Deliberately cut from v1.0

These were considered and left out on purpose. They are not fake TODOs: each one
is a real design decision, recorded so reviewers know what v1.0 does *not* claim.

1. **Real tokenizer.** Token counts come from a documented word/CJK estimate, not
   a BPE vocabulary. Shipping a real tokenizer means shipping a ~1 MB vocab and
   a merge-table replay loop; the estimate is honest about being an estimate and
   is only used to trigger the PA009 budget warning.
2. **No automatic rewriting / auto-fix.** The linter says what to change and why,
   but never edits the prompt. Automatic prompt rewriting without a model is a
   research problem, and a bad auto-fix is worse than no fix.
3. **No semantic scoring with an LLM.** Every number in this tool comes from
   deterministic string analysis so it can run in CI with zero network. A model-
   based quality score would not be reproducible between runs.
4. **No YAML block scalars / anchors.** The frontmatter parser supports the
   subset prompt files actually use; `|`, `>` and `&anchor` raise a clear error
   instead of being silently misparsed.
5. **No git integration.** `diff` takes two files, not a commit range. Wiring it
   to `git show` was cut to keep the dependency surface at zero; a `--from-git`
   flag is the first item below.

## Next

1. `prompt-atlas diff --git <rev>` to diff the working tree against a commit, so
   the polarity-flip veto can run in a pre-commit hook.
2. Rule severity configuration via a `prompt-atlas.toml` (per-project rule
   weights and suppression with a written justification).
3. A `--fix` mode limited to provably safe rewrites: whitespace, duplicate
   frontmatter keys, unbalanced braces, mixed placeholder dialects.
4. A published JSON Schema for the `--json` output so CI policies can validate
   the report before reading it.
5. Optional PyYAML extra for full YAML 1.2 frontmatter, while keeping the
   zero-dependency parser as the default.

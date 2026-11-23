# Frontmatter reference

`prompt-atlas` reads an optional YAML frontmatter block at the top of a prompt.
It is parsed by a zero-dependency YAML-lite parser (`src/prompt_atlas/frontmatter.py`),
not PyYAML, so the supported subset is documented here exactly.

## Keys the tool understands

| Key | Type | Used for |
| --- | --- | --- |
| `name` | string | shown in the lint card and reports |
| `version` | string or int | shown in the lint card |
| `model` | string | shown in the lint card |
| `vars` | list or mapping | declared template variables (PA010 / PA011) |
| `tags` | list | free-form, echoed in `--json` |

Any other key is preserved in `Document.meta` and echoed by `--json`; nothing
is silently dropped.

## Supported syntax

```yaml
---
name: support-agent
version: 2
model: gpt-4o
vars: [customer_message, order_id, tone]   # inline list
tags:
  - support                                 # block list
  - refunds
retry:
  attempts: 3                               # one level of nesting
  backoff: 1.5
---
```

Rules:

- Scalars: strings, integers, floats, `true`/`false`/`yes`/`no`, `null`/`~`.
- Quoted strings (`'...'` or `"..."`) keep `#` characters; otherwise a `#`
  preceded by whitespace starts a comment.
- Inline lists: `[a, b, c]`, including nested brackets and quoted items.
- Block lists: a key followed by lines starting with `- `.
- Nested mappings: one level of indentation (spaces only, never tabs).
- Duplicate keys are an error, not a silent overwrite.

## Error behaviour

Invalid frontmatter is a **usage error** (exit code 2), never a traceback, and
always names the offending line:

```console
$ python -m prompt_atlas lint examples/broken.md
prompt-atlas: error: examples/broken.md: duplicate key 'name' (frontmatter line 3)
```

## Not supported on purpose

| Feature | Why |
| --- | --- |
| Block scalars (`\|`, `>`) | Multi-line prompt bodies belong in the markdown, not the metadata |
| Anchors and aliases (`&a`, `*a`) | They make a config non-local and are a known deserialisation footgun |
| Custom tags (`!!python/...`) | Refused so a malicious prompt cannot instantiate objects |
| Multiple documents (`---` twice) | One prompt per file is the whole model |

Each of these raises a `FrontmatterError` with a line number rather than being
misparsed.

## Variable validation

`vars` is a contract, and both directions are checked:

- **PA010 `undeclared-variable`** - `{{tone}}` appears in the body but `tone` is
  not in `vars`. Severity is `error` when a frontmatter block exists (the file
  claims a contract and breaks it) and `warning` when the file has no
  frontmatter at all.
- **PA011 `unused-variable`** - `vars` declares `tone` but the body never uses
  `{{tone}}`. This is dead contract: callers pass a value and the model never
  sees it.

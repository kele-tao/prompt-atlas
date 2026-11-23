# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.x | yes |
| < 1.0 | no |

## Reporting a vulnerability

Open a private security advisory on GitHub
(`Security` tab -> `Report a vulnerability`) or email the maintainer listed in
`pyproject.toml`. Please do not open a public issue for anything that could leak
data. Expect a first response within a week.

## Threat model

prompt-atlas is an offline static analyser. It reads text files, writes the
report path you give it, and never opens a socket.

- **No network code at all.** There is no HTTP client in the dependency tree and
  no telemetry. You can run it in an air-gapped CI job.
- **No code execution from input.** Prompt files are parsed as text; frontmatter
  values are never `eval`-ed and YAML tags/anchors are rejected, so a malicious
  prompt cannot instantiate objects.
- **No shell.** The CLI never calls `subprocess`.
- **HTML reports escape everything** that comes from a prompt (prompt names, rule
  messages, fix hints) and contain no JavaScript, so a report is safe to open
  from an untrusted repository.

## The one thing it will tell on you

Rule PA012 scans prompt text for credential and PII shapes (emails, phone
numbers, AWS keys, bearer tokens, Luhn-valid card numbers). It reports the match
in the finding message, truncated to 24 characters. If you lint a prompt that
contains a *live* secret, that prefix ends up in your terminal and in any report
you commit. Treat a PA012 hit as an incident: rotate the credential first, then
remove it from the prompt.

## Dependencies

None at runtime. `pytest` and `ruff` are development-only.

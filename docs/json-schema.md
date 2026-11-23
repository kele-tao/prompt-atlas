# JSON output schema

`prompt-atlas lint --json` and `prompt-atlas report --format json` emit one
document. Keys are stable; new keys may be added in a minor release, existing
ones are never renamed.

```json
{
  "tool": "prompt-atlas",
  "version": "1.0.0",
  "prompts": [
    {
      "path": "examples/support-agent-v1.md",
      "name": "support-agent",
      "version": 1,
      "tokens": 246,
      "sections": 4,
      "instructions": 9,
      "score": {
        "total": 73.2,
        "grade": "B-",
        "axes": {
          "clarity": 70.0,
          "specificity": 85.0,
          "structure": 85.0,
          "constraints": 60.0,
          "examples": 94.0,
          "robustness": 54.0
        },
        "fixes": [
          {
            "rule": "PA006",
            "line": 24,
            "axis": "constraints",
            "impact": 5.0,
            "message": "contradictory directives: asked to be concise and detailed at the same time",
            "fix": "pick one: delete the weaker directive or scope each to a section"
          }
        ]
      },
      "findings": [
        {
          "rule": "PA006",
          "severity": "error",
          "line": 24,
          "message": "contradictory directives: asked to be concise and detailed at the same time",
          "hint": "pick one: delete the weaker directive or scope each to a section",
          "axis": "constraints",
          "deduction": 25.0
        }
      ]
    }
  ]
}
```

## Field notes

| Field | Meaning |
| --- | --- |
| `tokens` | Estimated tokens (word/4 plus one per CJK character) |
| `instructions` | Instruction units: bullets plus imperative sentences |
| `score.total` | Weighted mean of the six axes, 0-100, one decimal |
| `score.grade` | Letter grade derived from `total` |
| `score.fixes` | Up to 3 findings ranked by weight x deduction |
| `findings[].deduction` | Points removed from that axis for this finding |
| `findings[].line` | 1-based line in the source file, frontmatter included |

`prompt-atlas diff --json` wraps a single object:

```json
{
  "tool": "prompt-atlas",
  "version": "1.0.0",
  "diff": {
    "old": "examples/before.md",
    "new": "examples/after.md",
    "verdict": "mixed",
    "risk": "high",
    "risk_note": "2 polarity flip(s): ...",
    "token_delta": 257,
    "score_delta": 31.2,
    "sections_added": ["Constraints", "Example"],
    "sections_removed": [],
    "sections_modified": ["Triage"],
    "constraints_added": ["- You must answer in at most 120 words; ..."],
    "constraints_removed": [],
    "polarity_flips": [
      {
        "section": "Triage",
        "old": "If there are some issues, check the account and process the refund as needed.",
        "new": "- You must not promise a refund that the account history does not support.",
        "objects": ["account", "refund"]
      }
    ],
    "changes": [
      {"section": "Triage", "kind": "removed", "old_line": 9, "new_line": 0, "text": "..."}
    ]
  }
}
```

## CI recipe

```bash
prompt-atlas lint prompts/ --json > lint.json || true
jq -e '[.prompts[].findings[] | select(.severity == "error")] | length == 0' lint.json
```

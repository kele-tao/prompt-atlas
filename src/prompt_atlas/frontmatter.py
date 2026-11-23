"""A zero-dependency YAML-lite parser for prompt frontmatter.

Only the subset prompt files actually use is supported, documented in
`docs/frontmatter.md`:

* `key: scalar` (strings, ints, floats, booleans, `null`, quoted strings)
* `key: [a, b, c]` inline lists
* `key:` followed by `- item` block lists
* one level of nested `key:` + indented `child: value` mappings
* `#` comments on their own line or after a value

Anything else raises :class:`~prompt_atlas.model.FrontmatterError` with the
offending line number, because silently ignoring a typo in `vars` is how
prompts reach production with unrendered `{{placeholders}}`.
"""

from __future__ import annotations

import re
from typing import Any

from .model import FrontmatterError

KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*:\s*(.*)$")
LIST_ITEM_RE = re.compile(r"^\s*-\s*(.*)$")
TRUE_WORDS = {"true", "yes", "on"}
FALSE_WORDS = {"false", "no", "off"}
NULL_WORDS = {"null", "", "~"}


def _strip_comment(value: str) -> str:
    """Remove a trailing `#` comment that is not inside quotes."""
    quote = ""
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_scalar(raw: str) -> Any:
    """Turn one YAML-lite scalar into a Python value."""
    value = _strip_comment(raw).strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part) for part in _split_inline(inner)]
    text = _unquote(value)
    lowered = text.lower()
    if lowered in NULL_WORDS:
        return None
    if lowered in TRUE_WORDS:
        return True
    if lowered in FALSE_WORDS:
        return False
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?\d+\.\d+", text):
        return float(text)
    return text


def _split_inline(inner: str) -> list[str]:
    """Split `a, b, [c, d]` on top-level commas."""
    parts: list[str] = []
    depth = 0
    quote = ""
    current: list[str] = []
    for char in inner:
        if quote:
            current.append(char)
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            current.append(char)
        elif char == "[":
            depth += 1
            current.append(char)
        elif char == "]":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if "".join(current).strip():
        parts.append("".join(current))
    return [part.strip() for part in parts if part.strip()]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _parse_block(block: list[str], first_line: int, key: str) -> Any:
    meaningful = [line for line in block if not _is_blank(line)]
    if not meaningful:
        return None
    if all(LIST_ITEM_RE.match(line) for line in meaningful):
        items: list[Any] = []
        for line in meaningful:
            match = LIST_ITEM_RE.match(line)
            assert match is not None
            items.append(parse_scalar(match.group(1)))
        return items
    result: dict[str, Any] = {}
    base_indent = min(_indent(line) for line in meaningful)
    for offset, line in enumerate(block):
        if _is_blank(line):
            continue
        if _indent(line) != base_indent:
            raise FrontmatterError(
                "inconsistent indentation inside " + repr(key), first_line + offset
            )
        match = KEY_RE.match(line.strip())
        if not match:
            raise FrontmatterError(
                "expected 'key: value' inside " + repr(key), first_line + offset
            )
        result[match.group(1)] = parse_scalar(match.group(2))
    return result


def parse_frontmatter_lines(lines: list[str]) -> dict[str, Any]:
    """Parse the lines *between* the two `---` fences."""
    meta: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if _is_blank(line):
            index += 1
            continue
        if line.startswith("\t") or line.startswith(" \t"):
            raise FrontmatterError("tabs are not allowed for indentation", index + 1)
        match = KEY_RE.match(line)
        if not match:
            raise FrontmatterError(
                "expected 'key: value', got " + repr(line.strip()[:40]), index + 1
            )
        key, raw_value = match.group(1), match.group(2)
        if key in meta:
            raise FrontmatterError("duplicate key " + repr(key), index + 1)
        if _strip_comment(raw_value).strip():
            meta[key] = parse_scalar(raw_value)
            index += 1
            continue
        block: list[str] = []
        cursor = index + 1
        while cursor < len(lines):
            probe = lines[cursor]
            if _is_blank(probe):
                block.append("")
                cursor += 1
                continue
            if _indent(probe) == 0:
                break
            block.append(probe)
            cursor += 1
        meta[key] = _parse_block(block, index + 1, key)
        index = cursor
    return meta


def split_frontmatter(text: str) -> tuple[dict[str, Any], int, str]:
    """Return `(meta, frontmatter_line_count, body)` for a prompt document."""
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0, text
    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing = index
            break
    if closing is None:
        raise FrontmatterError("opening '---' is never closed", 1)
    meta = parse_frontmatter_lines(lines[1:closing])
    body_lines = lines[closing + 1 :]
    skipped = 0
    while body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]
        skipped += 1
    return meta, closing + 1 + skipped, "\n".join(body_lines)

"""Prompt loading and structural parsing.

The parser is deliberately tiny: markdown headings define sections, blank
lines separate blocks, and every metric the rules need is computed once here
so that rules stay pure functions over a :class:`Document`.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any

from .frontmatter import split_frontmatter
from .model import HEADING_RE, VAR_USE_RE, Document, PromptAtlasError, Section

CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uff00-\uffef]")
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
IMPERATIVE_RE = re.compile(
    r"^(?:always|never|do not|don't|use|avoid|return|respond|output|format|include|"
    r"exclude|ensure|keep|write|answer|reply|ask|refuse|escalate|follow|prefer|"
    r"begin|end|limit|cite|quote|summari[sz]e|classify|extract|generate|"
    r"you must|you should|you are|must|should)\b",
    re.IGNORECASE,
)
MODAL_RE = re.compile(
    r"\b(?:must|must not|should|should not|never|always|do not|don't|required|"
    r"forbidden|only|at most|at least)\b",
    re.IGNORECASE,
)
#: First words that make a line imperative; checked lower-case and cheaply.
IMPERATIVE_STARTS = frozenset(
    (
        "always", "never", "do", "don't", "use", "avoid", "return", "respond",
        "output", "format", "include", "exclude", "ensure", "keep", "write",
        "answer", "reply", "ask", "refuse", "escalate", "follow", "prefer",
        "begin", "end", "limit", "cite", "quote", "summarize", "summarise",
        "classify", "extract", "generate", "you", "must", "should",
    )
)

SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")
WORDISH_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")


def estimate_tokens(text: str) -> int:
    """Deterministic BPE-ish token estimate (word/4 + one per CJK character).

    This is an estimate, not a tokenizer: it is documented as within roughly
    10% for English prose and is used only for budget warnings.
    """
    if CJK_RE.search(text) is None:
        # Fast path: pure ASCII prose needs no substitution pass.  Words shorter
        # than four bytes all contribute exactly one token, so only the longer
        # ones need arithmetic.
        words = text.split()
        total = len(words)
        for chunk in words:
            size = len(chunk)
            if size > 4:
                total += (size - 1) // 4
        return total
    total = len(CJK_RE.findall(text))
    for chunk in CJK_RE.sub(" ", text).split():
        total += max(1, (len(chunk) + 3) // 4)
    return total


def _newline_offsets(text: str) -> list[int]:
    """Offsets of every newline, found with C-level `str.find` instead of a loop."""
    positions: list[int] = []
    index = text.find("\n")
    while index != -1:
        positions.append(index)
        index = text.find("\n", index + 1)
    return positions


def _iter_sentences(line: str) -> list[str]:
    return [part.strip() for part in SENTENCE_RE.findall(line) if part.strip()]


def count_instructions(lines: tuple[str, ...]) -> int:
    """Count actionable instruction units.

    A unit is a bullet/numbered item, or a sentence that is imperative or
    contains a modal keyword.  Prose counts as zero, which is what makes the
    `instr-count` rule meaningful.
    """
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if BULLET_RE.match(stripped):
            count += 1
            continue
        # One cheap lower-case scan decides whether the line can contain an
        # instruction at all; only then does the sentence split run.  On a 5 MB
        # prompt this is the difference between 0.5 s and 2.5 s.
        lowered = stripped.lower()
        start = lowered.split(" ", 2)[0].rstrip(":,.-")
        if start in IMPERATIVE_STARTS:
            count += 1
            continue
        if MODAL_RE.search(stripped) is None:
            continue
        for sentence in _iter_sentences(stripped):
            if IMPERATIVE_RE.match(sentence) or MODAL_RE.search(sentence):
                count += 1
    return count


def split_sections(lines: tuple[str, ...]) -> tuple[Section, ...]:
    """Split body lines into a preamble plus one section per heading."""
    sections: list[Section] = []
    pending_title = ""
    pending_level = 0
    buffer: list[str] = []
    current_start = 1
    for index, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            sections.append(
                Section(
                    title=pending_title,
                    level=pending_level,
                    start_line=current_start,
                    end_line=index - 1 if index > 1 else 0,
                    lines=tuple(buffer),
                )
            )
            pending_title = match.group(2).strip()
            pending_level = len(match.group(1))
            buffer = []
            current_start = index + 1
            continue
        buffer.append(line)
    sections.append(
        Section(
            title=pending_title,
            level=pending_level,
            start_line=current_start,
            end_line=len(lines),
            lines=tuple(buffer),
        )
    )
    # Drop an empty preamble so `sections` only contains real content.
    return tuple(s for s in sections if s.title or s.body.strip())


def _normalise_vars(meta: dict[str, Any]) -> tuple[str, ...]:
    raw = meta.get("vars")
    if raw is None:
        return ()
    if isinstance(raw, dict):
        return tuple(str(key) for key in raw)
    if isinstance(raw, str):
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if isinstance(raw, list):
        return tuple(str(item).strip() for item in raw if str(item).strip())
    return ()


def parse_document(text: str, path: str = "<text>") -> Document:
    """Parse prompt source text into a :class:`Document`."""
    meta, fm_lines, body = split_frontmatter(text)
    body_lines = tuple(body.splitlines())
    sections = split_sections(body_lines)
    used: list[str] = []
    for match in VAR_USE_RE.finditer(body):
        name = match.group(1)
        if name not in used:
            used.append(name)
    return Document(
        path=path,
        text=text,
        lines=body_lines,
        meta=meta,
        fm_line_count=fm_lines,
        sections=sections,
        token_count=estimate_tokens(body),
        instruction_count=count_instructions(body_lines),
        lower_body=body.lower(),
        newlines=tuple(_newline_offsets(body)),
        word_set=frozenset(WORDISH_RE.findall(body.lower())),
        vars_used=tuple(used),
        vars_declared=_normalise_vars(meta),
    )


def load_document(path: pathlib.Path | str) -> Document:
    """Read `path` (UTF-8) and parse it."""
    target = pathlib.Path(path)
    if target.is_dir():
        raise PromptAtlasError(f"expected a file, got a directory: {target}")
    try:
        text = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptAtlasError(f"no such file: {target}") from exc
    except IsADirectoryError as exc:
        raise PromptAtlasError(f"expected a file, got a directory: {target}") from exc
    except UnicodeDecodeError as exc:
        raise PromptAtlasError(
            f"{target} is not valid UTF-8 (byte {exc.start}); re-save it as UTF-8"
        ) from exc
    except OSError as exc:
        raise PromptAtlasError(f"cannot read {target}: {exc.strerror or exc}") from exc
    return parse_document(text, str(target))


def discover_prompts(path: pathlib.Path | str) -> list[pathlib.Path]:
    """Return prompt files under `path` (recursive, deterministic order)."""
    target = pathlib.Path(path)
    if target.is_file():
        return [target]
    if not target.exists():
        raise PromptAtlasError(f"no such file or directory: {target}")
    if not target.is_dir():
        raise PromptAtlasError(f"not a file or directory: {target}")
    suffixes = {".md", ".txt", ".prompt"}
    found = [
        item
        for item in target.rglob("*")
        if item.is_file()
        and item.suffix.lower() in suffixes
        and not any(part.startswith(".") for part in item.relative_to(target).parts)
        and "node_modules" not in item.parts
    ]
    found.sort(key=lambda item: item.as_posix())
    return found

"""Section-aware prompt diff with a risk verdict.

A plain line diff answers "what changed"; a prompt reviewer needs "what does
this change do to behaviour".  So the differ works section by section, pulls
out constraint lines (must / never / do not / at most ...), and looks for
polarity flips where the same action object moves between required and
forbidden.  The verdict is one of tightening, loosening, neutral or mixed.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from .model import Document

CONSTRAINT_RE = re.compile(
    r"\b(?:must|must not|never|always|do not|don't|required|forbidden|"
    r"at most|at least|limit(?:ed)? to|no more than|exactly)\b",
    re.IGNORECASE,
)
PROHIBITION_RE = re.compile(
    r"\b(?:not|never|avoid|forbidden|prohibited|refuse|decline)\b|n't\b", re.IGNORECASE
)
OBJECT_RE = re.compile(r"\b[A-Za-z]{4,}\b")
STOPWORDS = {
    "that", "this", "with", "from", "your", "have", "will", "must", "always",
    "never", "should", "when", "then", "than", "them", "they", "their", "there",
    "does", "each", "every", "some", "only", "also", "into", "over", "under",
    "more", "most", "less", "least", "answer", "response", "output", "format",
    "user", "prompt", "text", "like", "make", "sure",
}


@dataclass(frozen=True)
class LineChange:
    """One changed line, located by section."""
    section: str
    kind: str
    old_line: int
    new_line: int
    text: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "kind": self.kind,
            "old_line": self.old_line,
            "new_line": self.new_line,
            "text": self.text,
        }


@dataclass(frozen=True)
class PolarityFlip:
    """The same action object moved between required and forbidden."""
    section: str
    old_text: str
    new_text: str
    objects: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "old": self.old_text,
            "new": self.new_text,
            "objects": list(self.objects),
        }


@dataclass(frozen=True)
class DiffResult:
    """Everything the CLI and the reporters need to describe a change."""

    old_path: str
    new_path: str
    changes: tuple[LineChange, ...] = ()
    sections_added: tuple[str, ...] = ()
    sections_removed: tuple[str, ...] = ()
    sections_modified: tuple[str, ...] = ()
    constraints_added: tuple[str, ...] = ()
    constraints_removed: tuple[str, ...] = ()
    polarity_flips: tuple[PolarityFlip, ...] = ()
    verdict: str = "neutral"
    risk: str = "low"
    risk_note: str = ""
    token_delta: int = 0
    score_delta: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def added(self) -> int:
        return sum(1 for change in self.changes if change.kind == "added")

    @property
    def removed(self) -> int:
        return sum(1 for change in self.changes if change.kind == "removed")

    def as_dict(self) -> dict[str, Any]:
        return {
            "old": self.old_path,
            "new": self.new_path,
            "verdict": self.verdict,
            "risk": self.risk,
            "risk_note": self.risk_note,
            "added_lines": self.added,
            "removed_lines": self.removed,
            "token_delta": self.token_delta,
            "score_delta": round(self.score_delta, 1),
            "sections_added": list(self.sections_added),
            "sections_removed": list(self.sections_removed),
            "sections_modified": list(self.sections_modified),
            "constraints_added": list(self.constraints_added),
            "constraints_removed": list(self.constraints_removed),
            "polarity_flips": [flip.as_dict() for flip in self.polarity_flips],
            "changes": [change.as_dict() for change in self.changes],
        }


def _section_map(document: Document) -> dict[str, list[tuple[int, str]]]:
    mapping: dict[str, list[tuple[int, str]]] = {}
    for section in document.sections:
        key = section.title or "(preamble)"
        rows = [(section.start_line + offset, line) for offset, line in enumerate(section.lines)]
        mapping.setdefault(key, []).extend(rows)
    return mapping


@lru_cache(maxsize=16384)
def _objects(line: str) -> frozenset[str]:
    """Content words of a line, cached: the differ reuses lines heavily."""
    return frozenset(
        word.lower() for word in OBJECT_RE.findall(line) if word.lower() not in STOPWORDS
    )


def _is_constraint(line: str) -> bool:
    """True when the line states a hard requirement.

    Example payload lines such as ```order_id = "ORD-1"``` are skipped even if
    they happen to contain a marker word, because a value is not a rule.
    """
    match = CONSTRAINT_RE.search(line)
    if not match:
        return False
    assignment = line.find("=")
    return assignment == -1 or assignment > match.start()


def _constraint_polarity(line: str) -> str:
    return "negative" if PROHIBITION_RE.search(line) else "positive"


LCS_LINE_LIMIT = 400


def _opcodes(old_text: list[str], new_text: list[str]) -> list[tuple[str, int, int, int, int]]:
    """Diff opcodes, with a linear fallback for very large sections.

    difflib.SequenceMatcher is quadratic in the worst case, and prompt
    sections can be thousands of lines long.  Past LCS_LINE_LIMIT we trade
    line alignment quality for bounded time: prefix/suffix stay matched and
    the middle is reported as one replaced block, which is exactly what a
    reviewer needs at that size.
    """
    if max(len(old_text), len(new_text)) <= LCS_LINE_LIMIT:
        matcher = difflib.SequenceMatcher(a=old_text, b=new_text, autojunk=False)
        return matcher.get_opcodes()
    prefix = 0
    limit = min(len(old_text), len(new_text))
    while prefix < limit and old_text[prefix] == new_text[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < limit - prefix
        and old_text[len(old_text) - 1 - suffix] == new_text[len(new_text) - 1 - suffix]
    ):
        suffix += 1
    opcodes: list[tuple[str, int, int, int, int]] = []
    if prefix:
        opcodes.append(("equal", 0, prefix, 0, prefix))
    old_end = len(old_text) - suffix
    new_end = len(new_text) - suffix
    if prefix != old_end or prefix != new_end:
        opcodes.append(("replace", prefix, old_end, prefix, new_end))
    if suffix:
        opcodes.append(("equal", old_end, len(old_text), new_end, len(new_text)))
    return opcodes


def _flip_if_any(section: str, old_line: str, old_polarity: str, new_line: str) -> PolarityFlip | None:
    """Return a flip when one line inverts the requirement of another.

    A flip needs two shared action objects *and* a polarity change (a negation
    marker appearing or disappearing).  Requiring both is what keeps
    "do not mention X" / "do mention Y" from being reported as a flip when the
    only shared word is the noun.
    """
    overlap = _objects(old_line) & _objects(new_line)
    if len(overlap) < 2:
        return None
    new_polarity = _constraint_polarity(new_line)
    if old_polarity == new_polarity:
        return None
    return PolarityFlip(section, old_line.strip(), new_line.strip(), tuple(sorted(overlap)))


def diff_documents(old: Document, new: Document, score_delta: float = 0.0) -> DiffResult:
    """Compare two parsed prompts section by section."""
    old_sections = _section_map(old)
    new_sections = _section_map(new)
    old_keys = set(old_sections)
    new_keys = set(new_sections)

    added_sections = tuple(sorted(new_keys - old_keys))
    removed_sections = tuple(sorted(old_keys - new_keys))
    shared = sorted(old_keys & new_keys)

    changes: list[LineChange] = []
    modified: list[str] = []
    constraints_added: list[str] = []
    constraints_removed: list[str] = []
    # (section, text) for every changed line; polarity detection runs over these
    # through a word index, which keeps it near-linear even on a full rewrite.
    # A removed line may be a plain permission ("You may issue a refund"), so it
    # is not required to be a constraint - only the added side is.
    removed_constraints: list[tuple[str, str]] = []
    added_constraints: list[tuple[str, str]] = []

    for key in shared:
        old_rows = old_sections[key]
        new_rows = new_sections[key]
        old_text = [line.strip() for _, line in old_rows]
        new_text = [line.strip() for _, line in new_rows]
        section_changed = False
        for tag, i1, i2, j1, j2 in _opcodes(old_text, new_text):
            if tag == "equal":
                continue
            section_changed = True
            for index in range(i1, i2):
                text = old_rows[index][1].strip()
                if not text:
                    continue
                changes.append(LineChange(key, "removed", old_rows[index][0], 0, text))
                removed_constraints.append((key, text))
                if _is_constraint(text):
                    constraints_removed.append(text)
            for index in range(j1, j2):
                text = new_rows[index][1].strip()
                if not text:
                    continue
                changes.append(LineChange(key, "added", 0, new_rows[index][0], text))
                if _is_constraint(text):
                    constraints_added.append(text)
                added_constraints.append((key, text))
        if section_changed:
            modified.append(key)

    for key in added_sections:
        for number, text in new_sections[key]:
            if text.strip():
                stripped = text.strip()
                changes.append(LineChange(key, "added", 0, number, stripped))
                if _is_constraint(text):
                    constraints_added.append(stripped)
                added_constraints.append((key, stripped))
    for key in removed_sections:
        for number, text in old_sections[key]:
            if text.strip():
                stripped = text.strip()
                changes.append(LineChange(key, "removed", number, 0, stripped))
                removed_constraints.append((key, stripped))
                if _is_constraint(text):
                    constraints_removed.append(stripped)

    changed_constraints: set[str] = set()
    flips: list[PolarityFlip] = []
    seen_pairs: set[tuple[str, str]] = set()
    # The removed side may be a plain permission ("You may issue a refund"); the
    # added side must be a constraint, because that is the direction that makes a
    # prompt safer to obey and riskier to ship without re-testing.
    index: dict[str, list[int]] = {}
    for position, (_, text) in enumerate(added_constraints):
        for word in _objects(text):
            index.setdefault(word, []).append(position)
    for section, old_line in removed_constraints:
        old_polarity = _constraint_polarity(old_line)
        shared_counts: dict[int, int] = {}
        for word in _objects(old_line):
            for position in index.get(word, ()):
                shared_counts[position] = shared_counts.get(position, 0) + 1
        candidates = sorted(
            (position for position, count in shared_counts.items() if count >= 2)
        )
        for position in candidates:
            new_line = added_constraints[position][1]
            pair = (old_line, new_line)
            if pair in seen_pairs:
                continue
            flip = _flip_if_any(section, old_line, old_polarity, new_line)
            if flip is not None:
                seen_pairs.add(pair)
                changed_constraints.add(old_line)
                changed_constraints.add(new_line)
                flips.append(flip)
    # Constraints that moved rather than appearing or vanishing are reported as
    # a flip, not twice as a contradictory add/remove pair.
    constraints_added = [
        text for text in constraints_added if text.strip() not in changed_constraints
    ]
    constraints_removed = [
        text for text in constraints_removed if text.strip() not in changed_constraints
    ]

    verdict, risk, risk_note = _classify(
        len(constraints_added),
        len(constraints_removed),
        len(flips),
        added_sections,
        removed_sections,
    )
    return DiffResult(
        old_path=old.path,
        new_path=new.path,
        changes=tuple(changes),
        sections_added=added_sections,
        sections_removed=removed_sections,
        sections_modified=tuple(sorted(set(modified))),
        constraints_added=tuple(constraints_added),
        constraints_removed=tuple(constraints_removed),
        polarity_flips=tuple(flips),
        verdict=verdict,
        risk=risk,
        risk_note=risk_note,
        token_delta=new.token_count - old.token_count,
        score_delta=score_delta,
    )


def _classify(
    added: int,
    removed: int,
    flips: int,
    added_sections: tuple[str, ...],
    removed_sections: tuple[str, ...],
) -> tuple[str, str, str]:
    if flips:
        return (
            "mixed",
            "high",
            f"{flips} polarity flip(s): an action moved between required and forbidden. "
            "Any evaluation built on the old prompt is invalid until re-run.",
        )
    if added and not removed:
        note = "Only constraints were added, so output is narrower. Re-run goldens: valid answers may now be rejected."
        return "tightening", "medium", note
    if removed and not added:
        note = "Constraints were removed, so behaviour can regress silently. Keep the old prompt as a test fixture."
        return "loosening", "medium", note
    if added and removed:
        return (
            "mixed",
            "medium",
            "Constraints were both added and removed; review each one against the product requirement.",
        )
    if added_sections and not removed_sections:
        return "tightening", "low", "New section(s) added; the prompt gained scope, not strictness."
    if removed_sections and not added_sections:
        return "loosening", "medium", "Section(s) deleted; check that nothing depended on them."
    return "neutral", "low", "No constraint or polarity change detected."

"""The 20 static rules.

Every rule is a pure function `Document -> list[Issue]`.  Rules never mutate
state, never read the filesystem and never look at each other, which is what
makes the lint output reproducible and the rule set testable one rule at a
time.

Codes are stable and documented in the README; do not renumber them.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from .document import WORDISH_RE
from .model import Document, Issue

VAGUE_QUANTIFIERS = (
    "some",
    "several",
    "a few",
    "many",
    "various",
    "etc",
    "and so on",
    "as needed",
    "if necessary",
    "appropriate",
    "suitable",
    "relevant",
    "reasonable",
    "adequate",
    "a lot",
    "lots of",
    "stuff",
    "things",
    "better",
    "good",
    "nice",
)

AMBIGUOUS_VERBS = (
    "handle",
    "process",
    "manage",
    "deal with",
    "look at",
    "check",
    "improve",
    "optimize",
    "optimise",
    "fix",
    "help",
    "support",
    "consider",
    "work on",
)

ACRONYMS = {
    "JSON", "HTML", "XML", "YAML", "CSV", "TSV", "API", "APIS", "SQL", "URL",
    "URLS", "URI", "URIS", "HTTP", "HTTPS", "UUID", "LLM", "LLMS", "AI", "ID",
    "IDS", "OK", "PII", "CORS", "PDF", "CLI", "SDK", "MCP", "CPU", "RAM",
    "GPU", "UTC", "ISO", "RFC", "TLS", "SSL", "JWT", "OTP", "SLA", "KPI",
    "FAQ", "CRM", "CSAT", "NPS", "SRE", "CI", "CD", "PR", "QA", "UI", "UX",
    "NA", "USA", "EU", "UK", "AM", "PM", "README", "MIT", "ASCII", "UTF",
    "GB", "MB", "CEO", "CTO", "HR", "SSN", "AWS", "GCP", "ETA", "ASAP",
}

ALL_CAPS_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,}\b")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
BULLET_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
TERM_WORD_RE = re.compile(r"\b[A-Za-z]{3,}\b")
WORD_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
MID_SENTENCE_NAME_RE = re.compile(r"(?<=[a-z,;] )[A-Z][A-Za-z0-9]+")
MW_NAME_RE = re.compile(r"\b[A-Z][a-z][A-Za-z0-9]*(?:[ -][A-Z][A-Za-z0-9]+)+")

ROLE_PATTERNS = (
    r"\byou are (?:a|an|the|my)\b",
    r"\byou're (?:a|an|the|my)\b",
    r"\bact as (?:a|an|the)\b",
    r"\b(?:your|the) role is\b",
    r"\brole:\s*\w",
    r"\byour job is\b",
    r"\byour task is\b",
    r"\boperate as (?:a|an)\b",
)

OUTPUT_FORMAT_PATTERNS = (
    r"output format",
    r"response format",
    r"format your (?:answer|response|output)",
    r"\brespond (?:only )?(?:with|in|using)\b",
    r"\breturn (?:only )?(?:a |an )?(?:json|yaml|xml|csv|markdown|html|text)\b",
    r"\b(?:json|yaml|xml|csv|markdown)\b[^.\n]{0,40}\b(?:only|exactly|schema|object|array)\b",
    r"\bvalid json\b",
    r"\bno markdown\b",
    r"\buse (?:markdown|bullet points|a table)\b",
    r"\bformat:\s*\w",
)

EXAMPLE_PATTERNS = (
    r"\bfor example\b",
    r"\be\.g\.\b",
    r"^\s*(?:input|output|user|assistant|example|sample)\s*:",
    r"^\s*#{2,}\s*example",
)

STOP_CONDITION_PATTERNS = (
    r"\bstop\b",
    r"\bwhen (?:you are )?(?:done|finished)\b",
    r"\bif (?:you are )?(?:unsure|uncertain|not sure)\b",
    r"\bif (?:the )?(?:answer|information|details?) (?:is|are) (?:missing|unknown|unclear)\b",
    r"\bask (?:the user )?for clarification\b",
    r"\b(?:refuse|decline|escalate)\b",
    r"\bdo not (?:guess|invent|make up|hallucinate)\b",
    r"\bend (?:the|your) (?:response|answer|output)\b",
    r"\bmaximum of \d+ (?:words|sentences|tokens|bullets)\b",
)

CONSTRAINT_MARKERS = (
    r"\bmust\b",
    r"\bnever\b",
    r"\balways\b",
    r"\bdo not\b",
    r"\bdon't\b",
    r"\bat most\b",
    r"\bat least\b",
    r"\bonly\b",
    r"\brequired\b",
    r"\bforbidden\b",
    r"\blimit(?:ed)? to\b",
)

FAILURE_MODE_PATTERNS = (
    r"\bif (?:you are )?(?:unsure|uncertain|not sure|missing)\b",
    r"\bif (?:the )?(?:information|context|input) is (?:missing|incomplete|unavailable)\b",
    r"\bif\b[^.\n]{0,48}\b(?:missing|absent|unavailable|incomplete)\b",
    r"\bsay so\b",
    r"\bask (?:a )?(?:clarifying|follow[- ]up) question\b",
    r"\bdo not (?:guess|invent|fabricate|speculate)\b",
    r"\bwhen in doubt\b",
    r"\bstate (?:that|if) you (?:do not|don't) know\b",
    r"\bescalat(?:e|ion)\b",
)

INPUT_SPEC_PATTERNS = (
    r"\binput\b",
    r"\byou (?:will )?(?:receive|are given|get)\b",
    r"\bthe user (?:message|request|question|says)\b",
    r"\bgiven the following\b",
    r"\bcontext\b",
)


CONTRADICTION_PAIRS = (
    (
        r"\b(?:be|keep (?:it|the (?:answer|response))|stay|remain)\s+(?:very\s+)?(?:concise|brief|short|terse)\b",
        r"\b(?:explain|elaborate|expand|detailed|in[- ]depth|thorough|comprehensive|step[- ]by[- ]step|long[- ]form)\b",
        "asked to be concise and detailed at the same time",
    ),
    (
        r"\b(?:use|prefer|format (?:as|with))\s+(?:bullet(?:ed)? (?:points|lists)|bullets|numbered lists)\b",
        r"\b(?:prose|paragraphs?|narrative|continuous text)\b",
        "asked for bullet points and flowing prose at the same time",
    ),
    (
        r"\b(?:be|sound|stay|remain)\s+(?:formal|professional|corporate)\b",
        r"\b(?:casual|informal|friendly|conversational|chatty|slang)\b",
        "asked for both a formal and a casual register",
    ),
    (
        r"\b(?:always|must|required to)\s+(?:cite|quote|reference)\b",
        r"\b(?:never|do not|don't)\s+(?:cite|quote|reference)\b",
        "asked to cite sources and forbidden from citing them",
    ),
    (
        r"\b(?:be|stay|remain)\s+(?:creative|imaginative|inventive)\b",
        r"\b(?:deterministic|verbatim|exact|reproducible|factual only)\b",
        "asked for creative freedom and strict determinism",
    ),
    (
        r"\b(?:respond|answer|reply)\s+(?:only\s+)?(?:in|with)\s+(?:json|xml|yaml)\b",
        r"\b(?:respond|answer|reply)\s+(?:only\s+)?(?:in|with)\s+(?:prose|markdown|html|plain text)\b",
        "two mutually exclusive response formats are mandated",
    ),
)

FORMAT_MARKERS = {
    "json": r"\bjson\b",
    "yaml": r"\byaml\b",
    "xml": r"\bxml\b",
    "csv": r"\bcsv\b",
    "markdown": r"\bmarkdown\b",
    "html": r"\bhtml\b",
}

PII_PATTERNS = (
    ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "error"),
    (
        "phone",
        r"(?<![\w.-])(?:\+?\d{1,3}[ -]?)?(?:\(\d{3}\)[ -]?|\d{3}[ -])\d{3}[ -]\d{4}(?![\w.-])",
        "error",
    ),
    ("ssn", r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)", "error"),
    ("aws-key", r"\bAKIA[0-9A-Z]{16}\b", "error"),
    ("api-key", r"\b(?:sk|pk|rk)[-_][A-Za-z0-9]{16,}\b", "error"),
    ("private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "error"),
    ("bearer-token", r"\bBearer\s+[A-Za-z0-9._-]{20,}", "error"),
    (
        "ipv4",
        r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])",
        "warning",
    ),
)

CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")

def _compiled(patterns: Iterable[str], flags: int = re.IGNORECASE) -> tuple[re.Pattern, ...]:
    """Compile at import time: the rules scan multi-megabyte bodies."""
    return tuple(re.compile(pattern, flags) for pattern in patterns)


ROLE_RE = _compiled(ROLE_PATTERNS)
OUTPUT_FORMAT_RE = _compiled(OUTPUT_FORMAT_PATTERNS, re.IGNORECASE | re.MULTILINE)
EXAMPLE_RE = _compiled(EXAMPLE_PATTERNS, re.IGNORECASE | re.MULTILINE)
STOP_CONDITION_RE = _compiled(STOP_CONDITION_PATTERNS, re.IGNORECASE | re.MULTILINE)
FAILURE_MODE_RE = _compiled(FAILURE_MODE_PATTERNS)
CONSTRAINT_RE = _compiled(CONSTRAINT_MARKERS)
PII_RE = tuple((name, re.compile(pattern), severity) for name, pattern, severity in PII_PATTERNS)
FORMAT_RE = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in FORMAT_MARKERS.items()}
POLARITY_MARKERS = ("do not ", "don't ", "never ", "always ", "must ", "do ")
PHRASE_END_RE = re.compile(r"[.;]")
POLARITY_SCAN_LIMIT = 600
CONTRADICTION_RE = tuple(
    (re.compile(a, re.IGNORECASE | re.MULTILINE), re.compile(b, re.IGNORECASE | re.MULTILINE), why)
    for a, b, why in CONTRADICTION_PAIRS
)
TERM_RE = re.compile(r"\b[A-Za-z]{3,}\b")

VAGUE_RE = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in VAGUE_QUANTIFIERS) + r")\b", re.IGNORECASE
)

def _union(patterns: Iterable[str], flags: int = re.IGNORECASE | re.MULTILINE) -> re.Pattern:
    """Combine patterns into one non-capturing alternation.

    Each rule used to run 8-12 separate regex searches over the whole prompt,
    which dominated lint time on a 1 MB input.  Named groups would let us tell
    which alternative fired, but they are ~60x slower than a plain alternation
    in CPython, so this gate only answers "did anything in this group match?".
    When the answer is yes, the caller can afford to run the individual
    patterns to find out which one.
    """
    return re.compile("|".join("(?:%s)" % pattern for pattern in patterns), flags)


def _lowered_union(patterns: Iterable[str]) -> re.Pattern:
    """A case-insensitive alternation pre-applied to a lower-cased body.

    re.IGNORECASE costs about 2.5x a literal scan on a 5 MB string, and every
    keyword gate runs on `Document.lower_body` anyway, so the patterns are
    lower-cased once at import time instead.
    """
    return re.compile(
        "|".join("(?:%s)" % pattern.lower() for pattern in patterns), re.MULTILINE
    )


def _mentions(lower_body: str, keywords: tuple[str, ...]) -> bool:
    """Cheap substring prefilter for a pattern group.

    Each keyword list is a superset of the literals its patterns can match, so
    skipping the regex when none of them occur cannot change the result.  On a
    1 MB prompt this replaces ~12 full regex scans with a handful of C-level
    substring searches.
    """
    return any(keyword in lower_body for keyword in keywords)


CONTRADICTION_KEYWORDS = (
    "concise", "brief", "short", "terse", "detail", "elaborate", "expand", "thorough",
    "comprehensive", "bullet", "prose", "paragraph", "narrative", "formal", "casual",
    "informal", "friendly", "conversational", "cite", "quote", "reference", "creative",
    "imaginative", "deterministic", "verbatim", "reproducible", "respond", "answer",
    "reply", "json", "xml", "yaml", "markdown", "html", "plain text",
)
STOP_CONDITION_WORDS = frozenset(
    ("stop", "done", "finished", "unsure", "uncertain", "clarification", "refuse",
     "decline", "escalate", "guess", "invent", "hallucinate", "maximum")
)
FAILURE_MODE_WORDS = frozenset(
    ("unsure", "uncertain", "missing", "incomplete", "unavailable", "clarifying",
     "guess", "invent", "fabricate", "speculate", "doubt", "escalate", "escalation")
)


def _gate_hit(document: Document, words: frozenset[str]) -> bool:
    """True when the prompt contains any of these whole words (case-insensitive)."""
    return not document.word_set.isdisjoint(words)


ROLE_KEYWORDS = ("you are", "you're", "act as", "role", "your job", "your task", "operate as")
OUTPUT_FORMAT_KEYWORDS = (
    "format", "respond", "return", "json", "markdown", "yaml", "xml", "csv", "html",
    "bullet", "table", "text",
)
EXAMPLE_KEYWORDS = ("example", "e.g.", "input", "output", "user:", "assistant:", "sample", "~~~")
STOP_CONDITION_KEYWORDS = (
    "stop", "when", "if", "clarif", "refus", "declin", "escalat", "guess", "invent",
    "make up", "hallucinate", "end ", "maximum",
)
FAILURE_MODE_KEYWORDS = (
    "if", "clarif", "guess", "invent", "fabricat", "speculat", "doubt", "know",
    "escalat", "say so",
)
CONSTRAINT_KEYWORDS = (
    "must", "never", "always", "do not", "don't", "at most", "at least", "only",
    "required", "forbidden", "limit",
)
DIGIT_RUN_RE = re.compile(r"\d{3}")
#: A window of at least 8 characters that starts and ends with a digit: every
#: digit-shaped PII pattern needs one, so this single cheap pass replaces four
#: expensive ones over the whole prompt.
DIGIT_WINDOW_RE = re.compile(r"\d[\d\s().+-]{7,}\d")
DIGIT_PII = frozenset({"phone", "ssn", "ipv4"})

#: Literal substrings that must be present for a PII pattern to possibly match.
PII_HINTS = {
    "email": ("@",),
    "aws-key": ("akia",),
    "api-key": ("sk-", "pk-", "rk-", "sk_", "pk_", "rk_"),
    "private-key": ("-----begin",),
    "bearer-token": ("bearer",),
}


def _pii_hint(lower_body: str, name: str) -> bool:
    """Skip a PII pattern whose literal prefix is absent from the prompt."""
    hints = PII_HINTS.get(name)
    return True if hints is None else any(hint in lower_body for hint in hints)


VAGUE_KEYWORDS = tuple(word for word in VAGUE_QUANTIFIERS if " " not in word)
AMBIGUOUS_WORD_SET = frozenset(word for word in AMBIGUOUS_VERBS if " " not in word)
CAPS_GATE = re.compile(r"[A-Z]{3}")

ROLE_UNION = _lowered_union(ROLE_PATTERNS)
OUTPUT_FORMAT_UNION = _lowered_union(OUTPUT_FORMAT_PATTERNS)
EXAMPLE_UNION = _lowered_union(EXAMPLE_PATTERNS)
STOP_CONDITION_UNION = _lowered_union(STOP_CONDITION_PATTERNS)
FAILURE_MODE_UNION = _lowered_union(FAILURE_MODE_PATTERNS)
CONSTRAINT_UNION = _lowered_union(CONSTRAINT_MARKERS)


#: Literal gates for each contradiction pair, so the six regex pairs only run
#: when both sides could plausibly be present.  Order matches
#: CONTRADICTION_PAIRS.
CONTRADICTION_GATES = (
    (("concise", "brief", "short", "terse"), ("detail", "elaborate", "explain", "thorough")),
    (("bullet", "bullets", "numbered"), ("prose", "paragraph", "narrative")),
    (("formal", "professional"), ("casual", "informal", "friendly", "conversational")),
    (("cite", "quote", "reference"), ("cite", "quote", "reference")),
    (("creative", "imaginative", "inventive"), ("deterministic", "verbatim", "exact", "reproducible")),
    (("respond", "answer", "reply"), ("respond", "answer", "reply")),
)
CONTRADICTION_GATED = tuple(
    CONTRADICTION_GATES[index]
    + (re.compile(pair[0], re.IGNORECASE | re.MULTILINE),)
    + (re.compile(pair[1], re.IGNORECASE | re.MULTILINE),)
    + (pair[2],)
    for index, pair in enumerate(CONTRADICTION_PAIRS)
)

SEVERITY_ORDER = {"error": 2, "warning": 1, "info": 0}
SEVERITY_DEDUCTION = {"error": 25.0, "warning": 15.0, "info": 6.0}

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "are", "not", "have", "has", "will", "can", "may", "any", "all", "use",
    "when", "then", "than", "them", "they", "their", "there", "over", "under",
    "must", "always", "never", "each", "every", "some", "only", "also",
}


def _issue(
    code: str,
    severity: str,
    axis: str,
    message: str,
    line: int,
    hint: str,
) -> Issue:
    return Issue(
        rule=code,
        severity=severity,
        message=message,
        line=line,
        hint=hint,
        axis=axis,
        deduction=SEVERITY_DEDUCTION[severity],
    )


def _line_numbers(document: Document) -> Iterable[tuple[int, str]]:
    for index, line in enumerate(document.lines, start=1):
        yield index + document.fm_line_count, line


def _find_first(document: Document, pattern: str) -> int:
    compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    for number, line in _line_numbers(document):
        if compiled.search(line):
            return number
    return document.fm_line_count + 1


def line_of(document: Document, offset: int) -> int:
    """Map a character offset in the body to a 1-based file line number."""
    return document.line_for_offset(offset)


def from_offset(document: Document, offset: int) -> str:
    """The stripped source line containing a character offset (O(log n))."""
    index = document.line_index_for_offset(offset)
    if 0 <= index < len(document.lines):
        return document.lines[index].strip()
    return ""


def luhn_ok(digits: str) -> bool:
    """Luhn checksum: the difference between a card number and random noise."""
    cleaned = [int(ch) for ch in digits if ch.isdigit()]
    if not 13 <= len(cleaned) <= 19:
        return False
    total = 0
    for position, digit in enumerate(reversed(cleaned)):
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def rule_vague_quantifier(document: Document) -> list[Issue]:
    """PA001 - unmeasurable quantifiers make a prompt unreviewable."""
    if not _mentions(document.lower_body, VAGUE_KEYWORDS):
        return []
    match = VAGUE_RE.search(document.body)
    if match is None:
        return []
    word = match.group(1).lower()
    return [
        _issue(
            "PA001",
            "warning",
            "specificity",
            f"vague quantifier {word!r} - the model cannot act on it",
            line_of(document, match.start()),
            f"replace {word!r} with a countable rule, e.g. 'at most 3 examples'",
        )
    ]


def rule_ambiguous_verb(document: Document) -> list[Issue]:
    """PA002 - verbs like 'handle' hide the actual behaviour."""
    pattern = re.compile(
        r"\b("
        + "|".join(re.escape(v) for v in AMBIGUOUS_VERBS)
        + r")\b\s+(?:the|it|them|this|that|these|those)\b",
        re.IGNORECASE,
    )
    if not (document.word_set & AMBIGUOUS_WORD_SET):
        return []
    match = pattern.search(document.body)
    if match is None:
        return []
    return [
        _issue(
            "PA002",
            "warning",
            "clarity",
            f"ambiguous verb {match.group(0)!r} does not say what to do",
            line_of(document, match.start()),
            "name the operation: 'classify', 'summarise', 'extract', 'rewrite'",
        )
    ]


def rule_missing_role(document: Document) -> list[Issue]:
    """PA003 - no role framing means no stable persona."""
    head = "\n".join(document.lines[:15])
    head_lower = head.lower()
    if _mentions(head_lower, ROLE_KEYWORDS) and ROLE_UNION.search(head_lower):
        return []
    headings = " ".join(section.title for section in document.sections)
    if re.search(r"\b(role|persona|identity|you are)\b", headings, re.IGNORECASE):
        return []
    return [
        _issue(
            "PA003",
            "warning",
            "structure",
            "no role framing in the opening lines",
            document.fm_line_count + 1,
            "start with 'You are a <role> that <job>.' - it anchors tone and scope",
        )
    ]


def rule_missing_output_format(document: Document) -> list[Issue]:
    """PA004 - without a format contract the output shape floats."""
    lower = document.lower_body
    if _mentions(lower, OUTPUT_FORMAT_KEYWORDS) and OUTPUT_FORMAT_UNION.search(lower):
        return []
    return [
        _issue(
            "PA004",
            "warning",
            "specificity",
            "no output-format contract",
            document.fm_line_count + 1,
            "add an 'Output format' section: exact shape, field names, empty result",
        )
    ]


def rule_missing_examples(document: Document) -> list[Issue]:
    """PA005 - no worked example is the cheapest quality win available."""
    body = document.body
    if "```" in body or "~~~" in body:
        return []
    body_lower = body.lower()
    if _mentions(body_lower, EXAMPLE_KEYWORDS) and EXAMPLE_UNION.search(body_lower):
        return []
    return [
        _issue(
            "PA005",
            "info",
            "examples",
            "no worked example",
            document.fm_line_count + 1,
            "add one short input/output pair - it resolves most format ambiguity",
        )
    ]


def _polarity_phrases(
    document: Document,
) -> tuple[list[tuple[int, str, frozenset[str]]], list[tuple[int, str, frozenset[str]]]]:
    """Collect required and forbidden action phrases with their content words.

    Only lines that contain a polarity marker are considered at all, which
    keeps this rule cheap on long prompts.
    """
    forbidden: list[tuple[int, str, frozenset[str]]] = []
    required: list[tuple[int, str, frozenset[str]]] = []
    for number, line in _line_numbers(document):
        lowered = line.lower()
        if not any(marker in lowered for marker in POLARITY_MARKERS):
            continue
        # Cap the work on huge documents: the first few hundred directive
        # lines are enough to prove a contradiction, and the rule is advisory.
        if len(required) + len(forbidden) >= POLARITY_SCAN_LIMIT:
            break
        for marker in ("do not ", "don't ", "never "):
            position = lowered.find(marker)
            while position != -1:
                words = _phrase_words(lowered[position + len(marker) :])
                if words is not None:
                    forbidden.append((number, line.strip(), words))
                position = lowered.find(marker, position + 1)
        for marker in ("always ", "must ", "do "):
            position = lowered.find(marker)
            while position != -1:
                rest = lowered[position + len(marker) :]
                if not rest.startswith("not "):
                    words = _phrase_words(rest)
                    if words is not None:
                        required.append((number, line.strip(), words))
                position = lowered.find(marker, position + 1)
    return required, forbidden


def _phrase_words(rest: str) -> frozenset[str] | None:
    """Content words between a polarity marker and the next sentence end."""
    stop = PHRASE_END_RE.search(rest)
    phrase = rest[: stop.start()] if stop else rest
    words = frozenset(w for w in TERM_WORD_RE.findall(phrase) if w not in STOPWORDS)
    return words if len(words) >= 2 else None


def rule_contradiction(document: Document) -> list[Issue]:
    """PA006 - mutually exclusive directives, including polarity flips.

    A cheap keyword gate runs first: if no line contains a directive verb at
    all, there is nothing for the six pattern pairs or the polarity scan to
    find, and on a large prompt that gate saves several hundred milliseconds.
    """
    if not _mentions(document.lower_body, CONTRADICTION_KEYWORDS):
        return []
    lower = document.lower_body
    for gate_a, gate_b, pattern_a, pattern_b, description in CONTRADICTION_GATED:
        if not (_mentions(lower, gate_a) and _mentions(lower, gate_b)):
            continue
        match_a = pattern_a.search(document.body)
        if match_a is None:
            continue
        match_b = pattern_b.search(document.body)
        if match_b and match_a.start() != match_b.start():
            return [
                _issue(
                    "PA006",
                    "error",
                    "constraints",
                    f"contradictory directives: {description}",
                    line_of(document, match_b.start()),
                    "pick one: delete the weaker directive or scope each to a section",
                )
            ]
    required, forbidden = _polarity_phrases(document)
    # Compare through an inverted index instead of the full cross product: a
    # large prompt can contain thousands of directive lines and the naive
    # O(required x forbidden) loop is quadratic.
    index: dict[str, list[int]] = {}
    for position, (_, _, words) in enumerate(forbidden):
        for word in words:
            index.setdefault(word, []).append(position)
    for number, text, words in required:
        shared: dict[int, int] = {}
        for word in words:
            for position in index.get(word, ()):
                shared[position] = shared.get(position, 0) + 1
        for position in sorted(shared):
            if shared[position] < 2:
                continue
            other_number, other_text, _ = forbidden[position]
            if other_number == number:
                continue
            return [
                _issue(
                    "PA006",
                    "error",
                    "constraints",
                    f"polarity flip: {text[:48]!r} vs {other_text[:48]!r}",
                    number,
                    "the same action is both forbidden and required; keep the one "
                    "the product actually needs",
                )
            ]
    return []


def rule_missing_stop_condition(document: Document) -> list[Issue]:
    """PA007 - no stop condition means the model decides when to stop."""
    if _gate_hit(document, STOP_CONDITION_WORDS) and STOP_CONDITION_UNION.search(document.lower_body):
        return []
    return [
        _issue(
            "PA007",
            "warning",
            "constraints",
            "no stop condition or length bound",
            document.fm_line_count + 1,
            "add 'Stop after <n> bullets' or 'If the answer is not in the context, "
            "say so and stop.'",
        )
    ]


def rule_placeholder_collision(document: Document) -> list[Issue]:
    """PA008 - mixing template dialects breaks rendering."""
    body = document.body
    issues: list[Issue] = []
    if body.count("{{") != body.count("}}"):
        line = _find_first(document, r"\{\{|\}\}")
        issues.append(
            _issue(
                "PA008",
                "error",
                "structure",
                "unbalanced '{{' / '}}' placeholder delimiters",
                line,
                "close every '{{var}}'; an unbalanced brace renders as literal text",
            )
        )
    dialects: list[str] = []
    if "${" in body:
        dialects.append("${var}")
    if "<%" in body:
        dialects.append("<% var %>")
    if re.search(r"(?<!\{)\{[A-Za-z_][A-Za-z0-9_]*\}(?!\})", body):
        dialects.append("{var}")
    if re.search(r"\[[A-Z][A-Z0-9_]{2,}\]", body):
        dialects.append("[VAR]")
    if "{{" in body and dialects:
        line = _find_first(document, r"\$\{|<%|(?<!\{)\{[A-Za-z_]|\[[A-Z]{2,}\]")
        issues.append(
            _issue(
                "PA008",
                "warning",
                "structure",
                "mixed placeholder dialects: {{var}} plus " + ", ".join(dialects),
                line,
                "pick one dialect; a renderer only substitutes the one it was built for",
            )
        )
    return issues


def rule_prompt_too_long(document: Document) -> list[Issue]:
    """PA009 - long prompts cost tokens on every single call."""
    if document.token_count > 4000:
        return [
            _issue(
                "PA009",
                "error",
                "specificity",
                f"prompt is ~{document.token_count} tokens; context budget is burning",
                document.fm_line_count + 1,
                "move examples to a retrieval step and keep invariant rules under 2000 tokens",
            )
        ]
    if document.token_count > 1800:
        return [
            _issue(
                "PA009",
                "warning",
                "specificity",
                f"prompt is ~{document.token_count} tokens",
                document.fm_line_count + 1,
                "trim duplicated examples; every 1000 tokens is paid on every request",
            )
        ]
    return []


def rule_undeclared_variable(document: Document) -> list[Issue]:
    """PA010 - a placeholder that is never declared renders as raw braces."""
    if not document.vars_used:
        return []
    declared = set(document.vars_declared)
    missing = [name for name in document.vars_used if name not in declared]
    if not missing:
        return []
    severity = "error" if document.meta else "warning"
    line = _find_first(document, r"\{\{\s*" + re.escape(missing[0]) + r"\s*\}\}")
    return [
        _issue(
            "PA010",
            severity,
            "robustness",
            "undeclared placeholder" + ("s" if len(missing) > 1 else "") + ": " + ", ".join(missing),
            line,
            "declare them under 'vars:' in the frontmatter so callers and tests agree",
        )
    ]


def rule_unused_variable(document: Document) -> list[Issue]:
    """PA011 - a declared variable that is never used is dead contract."""
    if not document.vars_declared:
        return []
    used = set(document.vars_used)
    unused = [name for name in document.vars_declared if name not in used]
    if not unused:
        return []
    return [
        _issue(
            "PA011",
            "warning",
            "robustness",
            "declared but never used: " + ", ".join(unused),
            document.fm_line_count + 1,
            "delete the declaration, or reference it with {{" + unused[0] + "}}",
        )
    ]


def rule_secret_or_pii(document: Document) -> list[Issue]:
    """PA012 - real PII and credentials must not live in a prompt file."""
    issues: list[Issue] = []
    hint = "move it to a secret store and inject at call time; prompts get logged"
    # Run the whole-body patterns once instead of once per line: a 5 MB prompt
    # has ~90k lines and 8 patterns, which is the difference between 0.2 s and 5 s.
    # The card check needs digits; the keyword check skips the rest for plain prose.
    body = document.body
    lower = document.lower_body
    looks_sensitive = (
        "@" in lower
        or "bearer" in lower
        or "akia" in lower
        or "sk-" in lower
        or "pk-" in lower
        or "rk-" in lower
        or "private key" in lower
        or "-----begin" in lower
        or DIGIT_RUN_RE.search(body) is not None
    )
    hits: list[tuple[int, str, str, str]] = []
    if looks_sensitive:
        # Digit-shaped PII (phone, SSN, IPv4, cards) is validated only inside
        # windows that a single cheap pass has already flagged as digit-dense.
        windows = [(m.start(), m.group(0)) for m in DIGIT_WINDOW_RE.finditer(body)]
        for name, pattern, severity in PII_RE:
            if not _pii_hint(lower, name):
                continue
            if name in DIGIT_PII:
                for start, window in windows:
                    match = pattern.search(window)
                    if match and "{{" not in match.group(0):
                        hits.append((start + match.start(), name, severity, match.group(0)))
                continue
            for match in pattern.finditer(body):
                if "{{" in match.group(0):
                    continue
                hits.append((match.start(), name, severity, match.group(0)))
        hits.sort(key=lambda item: (item[0], item[1]))
    for position, name, severity, sample in hits:
        issues.append(
            _issue(
                "PA012",
                severity,
                "robustness",
                f"{name} pattern in prompt body: {sample[:24]!r}",
                line_of(document, position),
                hint,
            )
        )
    for match in (CARD_RE.finditer(body) if DIGIT_RUN_RE.search(body) else ()):
        candidate = match.group(0)
        if not luhn_ok(candidate):
            continue
        issues.append(
            _issue(
                "PA012",
                "error",
                "robustness",
                f"Luhn-valid card number in prompt body: {candidate[:6]}...",
                line_of(document, match.start()),
                "never ship card numbers in prompt text; use a fixture token",
            )
        )
    return issues


def rule_shouting(document: Document) -> list[Issue]:
    """PA013 - ALL-CAPS stops being emphasis when everything is emphasised."""
    body = document.body
    # Cheap gate: no run of three capitals means nothing can be shouting.
    if CAPS_GATE.search(body) is None:
        return []
    # One pass over the body: finditer gives positions, and only the first
    # offending line is needed for the finding.
    caps: list[tuple[int, str]] = []
    total_words = len(WORD_RE.findall(body))
    for match in ALL_CAPS_RE.finditer(body):
        token = match.group(0)
        if token in ACRONYMS:
            continue
        caps.append((line_of(document, match.start()), token))
    if len(caps) < 4 or total_words == 0:
        return []
    ratio = len(caps) / total_words
    if ratio < 0.12 and len(caps) < 8:
        return []
    sample = ", ".join(token for _, token in caps[:4])
    return [
        _issue(
            "PA013",
            "warning",
            "clarity",
            f"{len(caps)} ALL-CAPS words ({ratio:.0%} of the prompt): {sample}",
            caps[0][0],
            "keep caps for one hard constraint at most; use bold for the rest",
        )
    ]


def rule_too_many_instructions(document: Document) -> list[Issue]:
    """PA014 - instruction count past ~12 is where compliance drops."""
    if document.instruction_count <= 12:
        return []
    return [
        _issue(
            "PA014",
            "warning",
            "structure",
            f"{document.instruction_count} instruction units (soft limit 12)",
            document.fm_line_count + 1,
            "merge related bullets and move stable policy into a referenced section",
        )
    ]


def rule_no_constraints(document: Document) -> list[Issue]:
    """PA015 - no hard constraint means any output passes."""
    if not _mentions(document.lower_body, CONSTRAINT_KEYWORDS):
        return [
            _issue(
                "PA015",
                "warning",
                "constraints",
                "no hard constraints (must / never / at most)",
                document.fm_line_count + 1,
                "add two constraints you would actually reject a response for",
            )
        ]
    if CONSTRAINT_UNION.search(document.lower_body):
        return []
    return [
        _issue(
            "PA015",
            "warning",
            "constraints",
            "no hard constraints (must / never / at most)",
            document.fm_line_count + 1,
            "add two constraints you would actually reject a response for",
        )
    ]


def rule_no_failure_mode(document: Document) -> list[Issue]:
    """PA016 - nothing says what to do when the prompt cannot be satisfied."""
    if _gate_hit(document, FAILURE_MODE_WORDS) and FAILURE_MODE_UNION.search(document.lower_body):
        return []
    return [
        _issue(
            "PA016",
            "info",
            "robustness",
            "no failure-mode guidance",
            document.fm_line_count + 1,
            "say what to return when input is missing: 'If the order ID is absent, "
            "ask for it and stop.'",
        )
    ]


def rule_inconsistent_terminology(document: Document) -> list[Issue]:
    """PA017 - the same concept named two ways confuses the model and the team.

    Only mid-sentence proper nouns are compared (capitalised, not at the start
    of a line, not followed by a colon) because sentence-initial "Support" and
    heading capitalisation are not terminology drift.
    """
    # Two C-level scans instead of a Python loop over every token: collect the
    # capitalised names (multi-word sequences and mid-sentence single words),
    # then ask whether the same word also appears in lower case somewhere.
    body = document.body
    if MW_NAME_RE.search(body) is None and MID_SENTENCE_NAME_RE.search(body) is None:
        return []
    candidates: dict[str, tuple[str, int]] = {}
    for match in MW_NAME_RE.finditer(body):
        word = match.group(0)
        if word.upper() not in ACRONYMS:
            candidates.setdefault(word.lower(), (word, match.start()))
    for match in MID_SENTENCE_NAME_RE.finditer(body):
        word = match.group(0)
        if word.upper() not in ACRONYMS:
            candidates.setdefault(word.lower(), (word, match.start()))
    if not candidates:
        return []
    lower_tokens = set(WORDISH_RE.findall(document.lower_body))
    variants: dict[str, set[str]] = {}
    for key in sorted(candidates):
        word, start = candidates[key]
        if key not in lower_tokens and key not in document.lower_body:
            continue
        line = from_offset(document, start)
        if line.startswith("#") or line.startswith("```"):
            continue
        variants[key] = {word, key}
    for key in sorted(variants):
        forms = variants[key]
        if len(forms) > 1:
            return [
                _issue(
                    "PA017",
                    "info",
                    "clarity",
                    "inconsistent terminology: " + " vs ".join(sorted(forms)),
                    document.fm_line_count + 1,
                    "pick one spelling and use it everywhere, including examples",
                )
            ]
    return []


def rule_bullet_wall(document: Document) -> list[Issue]:
    """PA018 - a prompt that is 70% bullets has no prioritisation."""
    bullets = sum(1 for line in document.lines if BULLET_LINE_RE.match(line))
    non_blank = sum(1 for line in document.lines if line.strip())
    if bullets < 12 or non_blank == 0:
        return []
    if bullets / non_blank < 0.7:
        return []
    return [
        _issue(
            "PA018",
            "info",
            "structure",
            f"{bullets} bullets across {non_blank} non-blank lines - a wall of bullets",
            document.fm_line_count + 1,
            "group bullets under 3-5 headings so the model sees a hierarchy",
        )
    ]


def rule_no_input_spec(document: Document) -> list[Issue]:
    """PA019 - a template that never describes its input is guesswork at runtime."""
    if "{{" not in document.body:
        return []
    if re.search(r"^#{1,6}[ \t]+input\b", document.body, re.IGNORECASE | re.MULTILINE):
        return []
    if re.search(r"you (?:will )?(?:receive|are given|get)\b", document.body, re.IGNORECASE):
        return []
    if re.search(r"given the following", document.body, re.IGNORECASE):
        return []
    described = 0
    for name in document.vars_used:
        if re.search(r"`?" + re.escape(name) + r"`?\s*\(\s*[A-Za-z]", document.body):
            described += 1
    if described == len(document.vars_used) and described > 0:
        return []
    return [
        _issue(
            "PA019",
            "warning",
            "robustness",
            "placeholders are used but the input shape is never described",
            document.fm_line_count + 1,
            "add an 'Input' section: what each variable contains, its type and one example",
        )
    ]


def rule_conflicting_formats(document: Document) -> list[Issue]:
    """PA020 - two output formats named in the same format contract."""
    contract = re.search(
        r"output format|response format|return only|respond only", document.body, re.IGNORECASE
    )
    if not contract:
        return []
    window = document.body[contract.start() : contract.start() + 400]
    present = [
        name for name, pattern in FORMAT_RE.items() if pattern.search(window)
    ]
    if len(present) < 2:
        return []
    line = line_of(document, contract.start())
    return [
        _issue(
            "PA020",
            "info",
            "structure",
            "multiple output formats named: " + ", ".join(sorted(present)),
            line,
            "state which format is the answer and which are only allowed inside it",
        )
    ]


RULES: tuple[tuple[str, str, Callable[[Document], list[Issue]]], ...] = (
    ("PA001", "vague-quantifier", rule_vague_quantifier),
    ("PA002", "ambiguous-verb", rule_ambiguous_verb),
    ("PA003", "missing-role", rule_missing_role),
    ("PA004", "missing-output-format", rule_missing_output_format),
    ("PA005", "missing-example", rule_missing_examples),
    ("PA006", "contradictory-directive", rule_contradiction),
    ("PA007", "missing-stop-condition", rule_missing_stop_condition),
    ("PA008", "placeholder-collision", rule_placeholder_collision),
    ("PA009", "prompt-too-long", rule_prompt_too_long),
    ("PA010", "undeclared-variable", rule_undeclared_variable),
    ("PA011", "unused-variable", rule_unused_variable),
    ("PA012", "secret-or-pii", rule_secret_or_pii),
    ("PA013", "shouting", rule_shouting),
    ("PA014", "instruction-count", rule_too_many_instructions),
    ("PA015", "no-constraints", rule_no_constraints),
    ("PA016", "no-failure-mode", rule_no_failure_mode),
    ("PA017", "inconsistent-terminology", rule_inconsistent_terminology),
    ("PA018", "bullet-wall", rule_bullet_wall),
    ("PA019", "no-input-spec", rule_no_input_spec),
    ("PA020", "conflicting-formats", rule_conflicting_formats),
)

RULE_NAMES: dict[str, str] = {code: name for code, name, _ in RULES}


def run_rules(document: Document) -> list[Issue]:
    """Run every rule and return findings ordered by severity, code, line."""
    issues: list[Issue] = []
    for _, _, rule in RULES:
        issues.extend(rule(document))
    return sorted(
        issues, key=lambda issue: (-SEVERITY_ORDER[issue.severity], issue.rule, issue.line)
    )

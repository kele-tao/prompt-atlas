"""One or more focused assertions per rule: false negatives and false positives."""

from __future__ import annotations

from prompt_atlas import lint_text

stub = "You are a helpful support agent for a store.\n\n"


def codes(text: str) -> set[str]:
    return {issue.rule for issue in lint_text(text).issues}


def test_pa001_flags_vague_quantifier():
    assert "PA001" in codes(stub + "Summarise some of the tickets and add etc.")


def test_pa001_ignores_plain_text():
    assert "PA001" not in codes(stub + "Summarise every ticket in the queue.")


def test_pa002_flags_ambiguous_verb_with_object():
    assert "PA002" in codes(stub + "Handle the refund request carefully.")


def test_pa003_flags_missing_role():
    assert "PA003" in codes("# Task\nAnswer the question.")


def test_pa003_accepts_role_in_heading():
    assert "PA003" not in codes("## Role\nYou are a refunds analyst.\nAnswer the question.")


def test_pa004_flags_missing_output_format():
    assert "PA004" in codes(stub + "Answer the customer.")


def test_pa004_accepts_explicit_format():
    assert "PA004" not in codes(stub + "Output format: a JSON object with a reply field.")


def test_pa005_flags_missing_example():
    assert "PA005" in codes(stub + "Answer the customer.")


def test_pa006_flags_concise_plus_detailed():
    text = stub + "Be concise.\n\nExplain the reasoning in detail step by step."
    assert "PA006" in codes(text)


def test_pa006_flags_formal_plus_casual():
    text = stub + "Be professional at all times.\nUse a casual tone with everyone."
    assert "PA006" in codes(text)


def test_pa006_flags_polarity_flip():
    text = stub + "Always cite the policy document.\nNever cite the policy document."
    assert "PA006" in codes(text)


def test_pa007_flags_missing_stop_condition():
    assert "PA007" in codes(stub + "Write a summary of the ticket.")


def test_pa008_flags_unbalanced_braces():
    assert "PA008" in codes(stub + "Hello {{name}, welcome.")


def test_pa008_flags_mixed_dialects():
    assert "PA008" in codes(stub + "Hello {{name}} and ${other}.")


def test_pa009_flags_oversized_prompt():
    body = stub + "\n".join("This is a long invariant line number %d." % i for i in range(400))
    assert "PA009" in codes(body)


def test_pa010_flags_undeclared_variable():
    text = "---\nvars: [a]\n---\n" + stub + "Hello {{a}} {{b}}"
    assert "PA010" in codes(text)


def test_pa011_flags_unused_variable():
    text = "---\nvars: [a, b]\n---\n" + stub + "Hello {{a}}"
    assert "PA011" in codes(text)


def test_pa012_flags_email():
    assert "PA012" in codes(stub + "Contact dana@example.com for approvals.")


def test_pa012_flags_luhn_valid_card():
    assert "PA012" in codes(stub + "Use card 4242 4242 4242 4242 for the demo.")


def test_pa012_ignores_luhn_invalid_digits():
    assert "PA012" not in codes(stub + "Use order 1234 5678 9012 3456 as the example.")


def test_pa013_flags_shouting():
    text = stub + "ALWAYS ANSWER NICELY AND NEVER SHOUT AND ALWAYS BE POLITE OK."
    assert "PA013" in codes(text)


def test_pa013_allows_acronyms():
    text = stub + "Return JSON or YAML, never XML, and use the HTTP API with a UUID."
    assert "PA013" not in codes(text)


def test_pa014_flags_too_many_instructions():
    body = stub + "\n".join("- rule number %d" % i for i in range(20))
    assert "PA014" in codes(body)


def test_pa015_flags_missing_constraints():
    assert "PA015" in codes(stub + "Write a friendly summary of the ticket.")


def test_pa016_flags_missing_failure_mode():
    assert "PA016" in codes(stub + "Summarise the ticket.")


def test_pa016_accepts_escalation_guidance():
    text = stub + "If the customer is angry, escalate to a human."
    assert "PA016" not in codes(text)


def test_pa017_flags_proper_noun_drift():
    text = stub + "The Order Manager approves this. Then the order manager logs it."
    assert "PA017" in codes(text)


def test_pa018_flags_bullet_wall():
    body = stub + "\n".join("- bullet %d" % i for i in range(16))
    assert "PA018" in codes(body)


def test_pa019_flags_undescribed_placeholder():
    text = stub + "Write a reply for {{customer_message}}."
    assert "PA019" in codes(text)


def test_pa019_accepts_declared_input_section():
    text = stub + "## Input\n- `customer_message` (string): the message.\nWrite for {{customer_message}}."
    assert "PA019" not in codes(text)


def test_pa020_flags_two_formats_in_contract():
    text = stub + "Output format: return JSON wrapped in markdown fences."
    assert "PA020" in codes(text)


def test_every_rule_has_a_stable_code():
    from prompt_atlas.rules import RULES

    assert len(RULES) == 20
    assert len({code for code, _, _ in RULES}) == 20
    assert [code for code, _, _ in RULES] == ["PA%03d" % i for i in range(1, 21)]


def test_findings_are_sorted_by_severity():
    result = lint_text("# Task\nHandle the thing, some of it, etc. Be concise.\nExplain in detail.")
    severities = [issue.severity for issue in result.issues]
    order = {"error": 0, "warning": 1, "info": 2}
    assert severities == sorted(severities, key=lambda s: order[s])


def test_clean_prompt_has_no_errors():
    result = lint_text((__import__("pathlib").Path(__file__).parents[1] / "examples" / "support-agent.md").read_text(encoding="utf-8"))
    assert not result.errors

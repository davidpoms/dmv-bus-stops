from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

text = text.replace(
"    summarize_stop_evidence,",
"    summarize_stop_evidence,\n    generate_review_action_summary,"
)

old = """
    evidence_summary = summarize_stop_evidence(
        evidence
    )
"""

new = """
    evidence_summary = summarize_stop_evidence(
        evidence
    )

    review_actions = generate_review_action_summary(
        evidence,
        review_priority
    )
"""

if old not in text:
    raise Exception("Summary anchor missing")

text = text.replace(old,new)

old2 = """
            "evidence_summary": evidence_summary,
"""

new2 = """
            "evidence_summary": evidence_summary,

            "review_actions": review_actions,
"""

if old2 not in text:
    raise Exception("JSON anchor missing")

text = text.replace(old2,new2)

path.write_text(text)

print("Added review actions to API")

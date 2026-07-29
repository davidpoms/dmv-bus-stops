from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

text = text.replace(
"from src.assessment.interpretation import (",
"from src.assessment.interpretation import (\n    summarize_stop_evidence,"
)

old = """
    review_priority = interpret_review_priority(
        evidence,
        bench_status
    )
"""

new = """
    review_priority = interpret_review_priority(
        evidence,
        bench_status
    )

    evidence_summary = summarize_stop_evidence(
        evidence
    )
"""

if old not in text:
    raise Exception("API anchor not found")

text = text.replace(old,new)

old2 = """
            "evidence": evidence,
"""

new2 = """
            "evidence": evidence,

            "evidence_summary": evidence_summary,
"""

if old2 not in text:
    raise Exception("JSON anchor not found")

text = text.replace(old2,new2)

path.write_text(text)

print("Added evidence summary to API")

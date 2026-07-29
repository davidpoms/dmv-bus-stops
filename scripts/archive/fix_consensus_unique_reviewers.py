from pathlib import Path

p = Path("scripts/build_stop_consensus.py")

text = p.read_text()

old = """
    count = len(reviews)
"""

new = """
    reviewer_ids = {
        r["reviewer_id"]
        for r in reviews
        if r["reviewer_id"] is not None
    }

    count = len(reviewer_ids)
"""

if old not in text:
    print("Count block not found")
    raise SystemExit

text = text.replace(old, new)

p.write_text(text)

print("Consensus now counts unique reviewers")

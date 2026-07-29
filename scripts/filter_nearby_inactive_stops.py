from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()

old = """
            WHERE rq.community_review_available=1
            ORDER BY
                CASE
"""

new = """
            LEFT JOIN stop_wmata_evidence w
                ON rq.physical_stop_id = w.physical_stop_id
            WHERE rq.community_review_available=1
            AND (
                w.wmata_status IS NULL
                OR w.wmata_status != 'ABS'
            )
            ORDER BY
                CASE
"""

if old not in text:
    raise Exception("Could not find nearby query")

text = text.replace(old, new, 1)

p.write_text(text)

print("Filtered inactive stops from nearby reviews")

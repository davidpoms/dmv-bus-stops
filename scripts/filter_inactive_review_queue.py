from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()

old = """
            WHERE verification_needed=1
"""

new = """
            WHERE verification_needed=1
            AND physical_stop_id NOT IN (
                SELECT physical_stop_id
                FROM stop_wmata_evidence
                WHERE wmata_status='ABS'
            )
"""

if old not in text:
    raise Exception(
        "Could not find verification_needed filter"
    )

text = text.replace(
    old,
    new,
    1
)

p.write_text(text)

print("Filtered inactive stops from opportunity queue")

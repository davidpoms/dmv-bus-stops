from pathlib import Path

path = Path("src/review/create_review_queue.py")

text = path.read_text()

old = """
JOIN stop_wmata_evidence w

    ON w.physical_stop_id = ps.id

WHERE w.wmata_status = 'PRS'
"""

new = """
WHERE EXISTS (

    SELECT 1

    FROM stop_wmata_evidence w

    WHERE w.physical_stop_id = ps.id

    AND w.wmata_status = 'PRS'

)

AND NOT EXISTS (

    SELECT 1

    FROM stop_wmata_evidence w2

    WHERE w2.physical_stop_id = ps.id

    AND w2.wmata_status = 'ABS'

)
"""

if old not in text:
    raise Exception("Could not find query block")

text = text.replace(old,new)

path.write_text(text)

print("Patched review queue to strict PRS-only")
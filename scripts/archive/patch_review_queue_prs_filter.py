from pathlib import Path

path = Path("src/review/create_review_queue.py")

text = path.read_text(encoding="utf-8")

old = """
        SELECT

            io.physical_stop_id,
            io.priority_rank,
            io.opportunity_score,
            ps.primary_name

        FROM improvement_opportunities io

        JOIN physical_stops ps

            ON io.physical_stop_id = ps.id

        JOIN stop_wmata_evidence w

            ON w.physical_stop_id = ps.id

        WHERE w.wmata_status = 'PRS'

        ORDER BY io.priority_rank;
"""

new = """
        WITH latest_wmata AS (

            SELECT
                w1.physical_stop_id,
                w1.wmata_status

            FROM stop_wmata_evidence w1

            WHERE w1.id = (
                SELECT MAX(w2.id)
                FROM stop_wmata_evidence w2
                WHERE w2.physical_stop_id = w1.physical_stop_id
            )

        )

        SELECT DISTINCT

            io.physical_stop_id,
            io.priority_rank,
            io.opportunity_score,
            ps.primary_name

        FROM improvement_opportunities io

        JOIN physical_stops ps

            ON io.physical_stop_id = ps.id

        JOIN latest_wmata w

            ON w.physical_stop_id = ps.id

        WHERE w.wmata_status = 'PRS'

        ORDER BY io.priority_rank;
"""

if old not in text:
    raise Exception("Could not find old query block. File may have changed.")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("Patched create_review_queue.py with latest PRS-only WMATA filter")
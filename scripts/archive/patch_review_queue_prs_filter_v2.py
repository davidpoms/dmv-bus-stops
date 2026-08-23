from pathlib import Path

path = Path("src/review/create_review_queue.py")

text = path.read_text(encoding="utf-8")

start = text.find("    cursor.execute(")

end = text.find("    rows = cursor.fetchall()")

if start == -1 or end == -1:
    raise Exception("Could not find query section")

new_section = r'''    cursor.execute(
        """
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
    )


'''

text = text[:start] + new_section + text[end:]

path.write_text(text, encoding="utf-8")

print("Patched review queue query")
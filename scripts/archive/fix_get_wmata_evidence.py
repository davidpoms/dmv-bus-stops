from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.index("def get_wmata_evidence")
end = text.index("\ndef query_db", start)

replacement = r'''
def get_wmata_evidence(stop_id):

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT
            wmata_stop_id,
            wmata_status,
            wmata_bench,
            wmata_shelter,
            wmata_accessible,
            match_confidence,
            match_distance_m

        FROM stop_wmata_evidence

        WHERE physical_stop_id = ?

        ORDER BY
            CASE
                WHEN wmata_status = 'PRS'
                THEN 0
                ELSE 1
            END,
            match_distance_m ASC

        LIMIT 1
        """,
        (stop_id,)
    ).fetchone()

    conn.close()

    return dict(row) if row else None


'''

text = text[:start] + replacement + text[end:]

path.write_text(text)

print("Updated get_wmata_evidence")
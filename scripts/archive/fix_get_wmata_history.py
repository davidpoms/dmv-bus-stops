from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.index("def get_wmata_history")
end = text.index("\ndef get_wmata_evidence", start)

replacement = r'''
def get_wmata_history(stop_id):

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            wmata_stop_id,
            wmata_status,
            wmata_heading,
            wmata_bench,
            wmata_shelter,
            wmata_accessible,
            match_distance_m,
            match_confidence,
            created_at

        FROM stop_wmata_evidence

        WHERE physical_stop_id = ?

        ORDER BY
            created_at DESC,
            match_distance_m ASC
        """,
        (stop_id,)
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


'''

text = text[:start] + replacement + text[end:]

path.write_text(text)

print("Replaced get_wmata_history")
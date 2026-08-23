from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """
        LEFT JOIN stop_wmata_evidence w
        ON p.id = w.physical_stop_id
"""

new = """
        LEFT JOIN (
            SELECT *
            FROM stop_wmata_evidence
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        physical_stop_id,
                        ROW_NUMBER() OVER (
                            PARTITION BY physical_stop_id
                            ORDER BY
                                CASE
                                    WHEN wmata_status='PRS'
                                    THEN 0
                                    ELSE 1
                                END,
                                match_distance_m ASC
                        ) AS rn
                    FROM stop_wmata_evidence
                )
                WHERE rn = 1
            )
        ) w
        ON p.id = w.physical_stop_id
"""

if old not in text:
    raise Exception("Review WMATA join not found")

text = text.replace(old, new, 1)

path.write_text(text)

print("Patched review WMATA join")
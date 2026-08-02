from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """
        FROM active_wmata_evidence
        WHERE physical_stop_id = ?
"""


new = """
        FROM (
            SELECT
                physical_stop_id,
                wmata_status,
                wmata_bench,
                wmata_shelter,
                wmata_accessible,
                match_confidence,
                match_distance_m
            FROM active_wmata_evidence

            UNION ALL

            SELECT
                physical_stop_id,
                wmata_status,
                wmata_bench,
                wmata_shelter,
                wmata_accessible,
                match_confidence,
                match_distance_m
            FROM stop_wmata_evidence
        )

        WHERE physical_stop_id = ?

        ORDER BY
            CASE
                WHEN wmata_status='PRS' THEN 0
                ELSE 1
            END,

            match_distance_m

        LIMIT 1
"""


if old not in text:
    raise Exception("get_wmata_evidence query not found")


text = text.replace(old,new,1)


path.write_text(text)

print("Patched get_wmata_evidence with active fallback")
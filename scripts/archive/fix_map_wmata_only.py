from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


# 1. Add WMATA stop ID to SELECT
old = """
            SELECT DISTINCT

                ps.id,

                ps.primary_name,
"""

new = """
            SELECT DISTINCT

                ps.id,

                we.wmata_stop_id,

                ps.primary_name,
"""


if old not in text:
    raise Exception("Could not find SELECT block")

text = text.replace(old, new, 1)


# 2. Add WMATA evidence join
old = """
            FROM physical_stops ps

            LEFT JOIN improvement_opportunities io
"""

new = """
            FROM physical_stops ps

            JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            LEFT JOIN improvement_opportunities io
"""


if old not in text:
    raise Exception("Could not find FROM physical_stops block")

text = text.replace(old, new, 1)


path.write_text(text, encoding="utf-8")

print("Updated map_stops() to use WMATA evidence and return WMATA stop ID")
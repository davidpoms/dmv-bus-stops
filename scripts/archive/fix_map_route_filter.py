from pathlib import Path
import shutil

APP = Path("src/api/app.py")

backup = Path("src/api/app_before_route_filter_fix.py")

print("Backing up...")
shutil.copy(APP, backup)

text = APP.read_text(encoding="utf-8")


old = """
            JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            JOIN improvement_opportunities io
                ON ps.id = io.physical_stop_id
"""

new = """
            LEFT JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            LEFT JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            JOIN improvement_opportunities io
                ON ps.id = io.physical_stop_id
"""


if old not in text:
    print("Could not find first JOIN block")
else:
    text = text.replace(old, new, 1)


old2 = """
            JOIN bus_stops bs
                ON psm.bus_stop_id = bs.id

            JOIN stop_routes sr
                ON bs.id = sr.stop_id

            LEFT JOIN stop_jurisdiction sj
"""

new2 = """
            LEFT JOIN bus_stops bs
                ON psm.bus_stop_id = bs.id

            LEFT JOIN stop_routes sr
                ON bs.id = sr.stop_id

            LEFT JOIN stop_jurisdiction sj
"""


if old2 not in text:
    print("Could not find route JOIN block")
else:
    text = text.replace(old2, new2, 1)


old3 = """
            WHERE sr.route_id = ?
"""

new3 = """
            WHERE (
                ? IS NULL
                OR sr.route_id = ?
            )
"""


if old3 not in text:
    print("Could not find route WHERE")
else:
    text = text.replace(old3, new3, 1)


APP.write_text(text, encoding="utf-8")

print("Done.")
print("Backup saved:", backup)
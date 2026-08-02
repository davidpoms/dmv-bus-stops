from pathlib import Path
import shutil

APP = Path("src/api/app.py")
BACKUP = Path("src/api/app_before_transit_join_fix.py")

shutil.copy(APP, BACKUP)

text = APP.read_text(encoding="utf-8")


old = """
            JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            JOIN stop_transit_evidence ste
                ON psm.bus_stop_id = ste.stop_id
                AND ste.gtfs_bus_stop = 1
"""

new = """
            JOIN stop_transit_evidence ste
                ON ps.id = ste.stop_id
                AND ste.gtfs_bus_stop = 1

            LEFT JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id
"""


if old not in text:
    print("Could not find old transit join")
else:
    text = text.replace(old, new, 1)
    print("Fixed transit evidence join")


APP.write_text(text, encoding="utf-8")

print("Backup:", BACKUP)
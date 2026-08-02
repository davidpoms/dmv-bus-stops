from pathlib import Path
import shutil


path = Path("src/api/app.py")

backup = Path("src/api/app.py.backup_before_active_wmata_filter")

shutil.copy(path, backup)

text = path.read_text()


old = """
            FROM physical_stops ps
"""

new = """
            FROM physical_stops ps

            JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            JOIN stop_transit_evidence ste
                ON psm.bus_stop_id = ste.stop_id
                AND ste.gtfs_bus_stop = 1
"""


start = text.find("def map_stops()")

if start == -1:
    raise Exception("Could not find map_stops function")


before = text[:start]
after = text[start:]


count = after.count(old)

if count != 2:
    raise Exception(
        f"Expected 2 map SQL blocks, found {count}"
    )


after = after.replace(old, new, 2)


path.write_text(before + after)

print(
    "Updated map_stops() with active WMATA filter"
)

print(
    "Backup:",
    backup
)
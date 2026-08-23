from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/api/app.py")

backup = Path(
    f"src/api/app_backup_before_geojson_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


old = """
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            row[3],
                            row[2]
                        ]
                    },

                    "properties": {
                        "stop_id": row[0],
                        "location": row[1],
                        "score": row[4],
                        "impact": row[5],
                        "priority": row[6],
                        "validation_status": row[7],
                        "action_status": row[8]
                    }
"""


new = """
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            row[4],
                            row[3]
                        ]
                    },

                    "properties": {
                        "stop_id": row[0],
                        "wmata_stop_id": row[1],
                        "location": row[2],
                        "score": row[5],
                        "impact": row[6],
                        "priority": row[7],
                        "validation_status": row[8],
                        "action_status": row[9]
                    }
"""


if old not in text:
    raise Exception(
        "Could not find GeoJSON property block"
    )


text = text.replace(
    old,
    new,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("GeoJSON mapping updated")
from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
            "spreadsheet_id": row[0],
            "api_id": row[1],
            "lifecycle_status": row[2],
            "routes": row[3].split(",") if row[3] else [],
            "route_count": row[4],
            "shelter_present": bool(row[5]),
            "confidence": row[6],
            "notes": row[7]
"""


new = """
            "physical_stop_id": row[0],
            "ddot_id": row[1],
            "api_id": row[2],
            "lifecycle_status": row[3],
            "routes": row[4].split(",") if row[4] else [],
            "route_count": row[5],
            "confidence": row[6],
            "notes": row[7]
"""


if old not in text:
    raise Exception("Old DDOT payload mapping not found")


text = text.replace(old, new)

path.write_text(
    text,
    encoding="utf-8"
)

print("Fixed DDOT payload mapping")
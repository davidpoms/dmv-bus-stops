from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


text = text.replace(
"""
        SELECT
            physical_stop_id,
            source_record_id,
            api_id,
            lifecycle_status,
            routes,
            route_count,
            present,
            confidence,
            notes
        FROM stop_ddot_shelter_evidence
        WHERE physical_stop_id = ?
""",
"""
        SELECT
            spreadsheet_id,
            api_id,
            lifecycle_status,
            routes,
            route_count,
            present,
            confidence,
            notes
        FROM stop_ddot_shelter_evidence
        WHERE physical_stop_id = ?
"""
)


text = text.replace(
"""
            "physical_stop_id": row[0],
            "source_record_id": row[1],
            "api_id": row[2],
            "lifecycle_status": row[3],
            "routes": row[4].split(",") if row[4] else [],
            "route_count": row[5],
            "shelter_present": bool(row[6]),
            "confidence": row[7],
            "notes": row[8]
""",
"""
            "spreadsheet_id": row[0],
            "api_id": row[1],
            "lifecycle_status": row[2],
            "routes": row[3].split(",") if row[3] else [],
            "route_count": row[4],
            "shelter_present": bool(row[5]),
            "confidence": row[6],
            "notes": row[7]
"""
)


path.write_text(text, encoding="utf-8")

print("Fixed DDOT stop evidence schema mapping")
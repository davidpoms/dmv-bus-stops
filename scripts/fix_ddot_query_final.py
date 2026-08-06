from pathlib import Path


APP = Path("src/api/app.py")

text = APP.read_text(encoding="utf-8")


start = text.find(
    "    ddot_evidence = query_db("
)

end = text.find(
    "\n\n    ddot_evidence_payload = [",
    start
)


if start == -1 or end == -1:
    raise Exception(
        "Could not find DDOT query section"
    )


replacement = """
    ddot_evidence = query_db(
        '''
        SELECT
            physical_stop_id,
            ddot_id,
            api_id,
            lifecycle_status,
            route_ids,
            route_count,
            confidence,
            notes
        FROM stop_ddot_shelter_evidence
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )
"""


text = (
    text[:start]
    + replacement
    + text[end:]
)


# Fix payload mapping too
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
            "physical_stop_id": row[0],
            "ddot_id": row[1],
            "api_id": row[2],
            "lifecycle_status": row[3],
            "routes": row[4].split(",") if row[4] else [],
            "route_count": row[5],
            "confidence": row[6],
            "notes": row[7]
"""
)


APP.write_text(
    text,
    encoding="utf-8"
)


print("Fixed DDOT evidence schema mapping")
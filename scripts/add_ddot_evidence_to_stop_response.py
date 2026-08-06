from pathlib import Path


APP = Path("src/api/app.py")

text = APP.read_text(encoding="utf-8")


# Add DDOT evidence lookup after wmata evidence lookup
old = """
    wmata_history = get_wmata_history(stop_id)

    wmata_evidence = get_wmata_evidence(stop_id)
"""

new = """
    wmata_history = get_wmata_history(stop_id)

    wmata_evidence = get_wmata_evidence(stop_id)


    ddot_evidence = query_db(
        '''
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
        ''',
        (stop_id,)
    )


    ddot_evidence_payload = [
        {
            "physical_stop_id": row[0],
            "source_record_id": row[1],
            "api_id": row[2],
            "lifecycle_status": row[3],
            "routes": row[4].split(",") if row[4] else [],
            "route_count": row[5],
            "shelter_present": bool(row[6]),
            "confidence": row[7],
            "notes": row[8]
        }
        for row in ddot_evidence
    ]
"""

if old not in text:
    raise Exception("Could not find wmata lookup section")

text = text.replace(old, new)


old2 = """
            "wmata_evidence":
                wmata_evidence,
"""

new2 = """
            "wmata_evidence":
                wmata_evidence,


            "ddot_evidence":
                ddot_evidence_payload,
"""

if old2 not in text:
    raise Exception("Could not find wmata response field")

text = text.replace(old2, new2)


APP.write_text(text, encoding="utf-8")

print("Added DDOT evidence to stop API response")
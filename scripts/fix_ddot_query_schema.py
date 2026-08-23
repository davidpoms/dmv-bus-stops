from pathlib import Path


APP = Path("src/api/app.py")

text = APP.read_text()


old = """
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
"""


new = """
    ddot_evidence = query_db(
        '''
        SELECT
            physical_stop_id,
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
        ''',
        (stop_id,)
    )
"""


if old not in text:
    raise Exception(
        "DDOT query block not found"
    )


text = text.replace(old, new)


old_payload = """
            "source_record_id": row[1],
"""


new_payload = """
            "spreadsheet_id": row[1],
"""


if old_payload not in text:
    raise Exception(
        "DDOT payload field not found"
    )


text = text.replace(
    old_payload,
    new_payload
)


APP.write_text(text)

print(
    "Fixed DDOT API schema references"
)
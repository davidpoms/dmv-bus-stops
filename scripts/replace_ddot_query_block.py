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
        "Could not locate DDOT evidence section"
    )


replacement = """
    ddot_evidence = query_db(
        '''
        SELECT
            physical_stop_id,
            ddot_id,
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


text = (
    text[:start]
    + replacement
    + text[end:]
)


APP.write_text(
    text,
    encoding="utf-8"
)


print(
    "Replaced DDOT query block"
)
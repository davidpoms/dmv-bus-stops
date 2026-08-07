from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text(encoding="utf-8")


# Find review endpoint only
start = text.index('@app.route("/review/<int:stop_id>/info")')
end = text.index('@app.route("/review/<int:stop_id>/assignment")')

section = text[start:end]


if "ddot_interpretation" in section:
    print("DDOT already exists in review endpoint")
    raise SystemExit


# Insert query after row = stop[0]
section = section.replace(
"""    row = stop[0]


""",
"""    row = stop[0]


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


    ddot_evidence_payload = [
        {
            "physical_stop_id": r[0],
            "ddot_id": r[1],
            "api_id": r[2],
            "lifecycle_status": r[3],
            "routes": r[4].split(",") if r[4] else [],
            "route_count": r[5],
            "confidence": r[6],
            "notes": r[7]
        }
        for r in ddot_evidence
    ]


    ddot_interpretation = interpret_ddot_evidence(
        ddot_evidence_payload
    )


""",
1
)


# Insert into JSON before community_reviews
section = section.replace(
"""
            "community_reviews": {
""",
"""
            "ddot_evidence":
                ddot_evidence_payload,


            "ddot_interpretation":
                ddot_interpretation,


            "community_reviews": {
""",
1
)


text = (
    text[:start]
    + section
    + text[end:]
)


p.write_text(text, encoding="utf-8")

print("Review endpoint patched")
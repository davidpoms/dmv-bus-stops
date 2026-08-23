from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
    ddot_interpretation = interpret_ddot_evidence(
        ddot_evidence_payload
    )


    wmata_history = get_wmata_history(stop_id)
"""


new = """
    wmata_history = get_wmata_history(stop_id)
"""


if old not in text:
    raise Exception(
        "Could not find early DDOT interpretation block"
    )


text = text.replace(
    old,
    new,
    1
)


marker = """
    ddot_evidence_payload = [
        {
            "physical_stop_id": row[0],
            "ddot_id": row[1],
            "api_id": row[2],
            "lifecycle_status": row[3],
            "routes": row[4].split(",") if row[4] else [],
            "route_count": row[5],
            "confidence": row[6],
            "notes": row[7]
        }
        for row in ddot_evidence
    ]
"""


insert = marker + """


    ddot_interpretation = interpret_ddot_evidence(
        ddot_evidence_payload
    )
"""


if marker not in text:
    raise Exception(
        "Could not find DDOT payload block"
    )


text = text.replace(
    marker,
    insert,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Moved DDOT interpretation after payload creation"
)
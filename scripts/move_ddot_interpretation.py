from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


bad = """
    ddot_interpretation = interpret_ddot_evidence(
        ddot_evidence_payload
    )


    ddot_evidence_payload = [
"""


good = """
    ddot_evidence_payload = [
"""


if bad not in text:
    raise Exception(
        "Could not find misplaced DDOT interpretation"
    )


text = text.replace(
    bad,
    good
)


marker = """
    ]


    wmata_history = get_wmata_history(stop_id)
"""


replacement = """
    ]


    ddot_interpretation = interpret_ddot_evidence(
        ddot_evidence_payload
    )


    wmata_history = get_wmata_history(stop_id)
"""


if marker not in text:
    raise Exception(
        "Could not find payload end marker"
    )


text = text.replace(
    marker,
    replacement,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Moved DDOT interpretation after payload creation"
)
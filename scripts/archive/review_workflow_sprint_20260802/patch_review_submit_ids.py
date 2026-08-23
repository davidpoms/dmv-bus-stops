from pathlib import Path

html = Path("src/dashboard/templates/review.html")

text = html.read_text(encoding="utf-8")


marker = """
payload.stop_id =
stopId;
"""


replacement = """
payload.stop_id =
stopId;


payload.assignment_id =
    document.getElementById("assignment_id").value;

payload.reviewer_id =
    document.getElementById("reviewer_id").value;
"""


if marker not in text:
    raise RuntimeError(
        "Could not find stop_id payload block"
    )


text = text.replace(marker, replacement)

html.write_text(text, encoding="utf-8")

print("Added explicit review identifiers to submit payload.")
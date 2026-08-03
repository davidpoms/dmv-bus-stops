from pathlib import Path

html = Path("src/dashboard/templates/review.html")

text = html.read_text(encoding="utf-8")


old = """
    const assignmentId =
        params.get("assignment_id");


    if (!assignmentId) {

        console.error(
            "Missing assignment id"
        );

        return;

    }


    const response =
        await fetch(
            `/review/${stopId}/assignment?assignment_id=${assignmentId}`
        );
"""


new = """
    const assignmentId =
        params.get("assignment_id");


    let assignmentUrl =
        `/review/${stopId}/assignment`;


    if (assignmentId) {

        assignmentUrl +=
            `?assignment_id=${assignmentId}`;

    }


    const response =
        await fetch(
            assignmentUrl
        );
"""


if old not in text:
    raise RuntimeError(
        "Could not find assignment loader block"
    )


text = text.replace(old, new)

html.write_text(text, encoding="utf-8")

print("Updated assignment loader to allow backend assignment creation.")
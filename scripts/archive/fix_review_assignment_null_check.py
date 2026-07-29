from pathlib import Path

p = Path("src/dashboard/templates/review.html")

text = p.read_text()


old = """
    const assignmentId =
        params.get("assignment");


    const response =
        await fetch(
            `/review/${stopId}/assignment?assignment_id=${assignmentId}`
        );
"""


new = """
    const assignmentId =
        params.get("assignment");


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


if old not in text:
    raise Exception(
        "Could not find assignment loader block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Added assignment id guard"
)

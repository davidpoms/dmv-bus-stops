from pathlib import Path

p = Path("src/dashboard/templates/review.html")
text = p.read_text()

if "review/${stopId}/assignment" in text:
    print("Assignment loader already present.")
    raise SystemExit

insert = r"""

// Load assignment information
(async () => {

    const res = await fetch(
        `/review/${stopId}/assignment`
    );

    const assignment = await res.json();

    document.getElementById("reviewer_id").value =
        assignment.reviewer_id;

    document.getElementById("assignment_id").value =
        assignment.assignment_id;

    document.getElementById("stopInfo").innerHTML =
        `
        <strong>Stop ${assignment.stop_id}</strong><br>
        Reviewer #${assignment.reviewer_id}
        `;

})();

"""

text = text.replace(
    'const stopId =\nwindow.location.pathname.split("/").pop();',
    'const stopId =\nwindow.location.pathname.split("/").pop();'
    + insert
)

p.write_text(text)
print("Added assignment loader.")

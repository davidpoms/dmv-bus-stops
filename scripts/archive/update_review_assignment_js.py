from pathlib import Path

p = Path("src/dashboard/templates/review.html")

text = p.read_text()

marker = """
const stopId =
window.location.pathname.split("/").pop();

"""

insert = """
const stopId =
window.location.pathname.split("/").pop();


async function loadAssignment(){

    const response =
        await fetch(
            `/review/${stopId}/assignment`
        );

    const data =
        await response.json();


    document
    .getElementById("assignment_id")
    .value =
        data.assignment_id;


    document
    .getElementById("reviewer_id")
    .value =
        data.reviewer_id;

}


loadAssignment();

"""

if "function loadAssignment()" not in text:

    text = text.replace(
        marker,
        insert
    )

    p.write_text(text)

    print("Added assignment loader")

else:
    print("Assignment loader already exists")


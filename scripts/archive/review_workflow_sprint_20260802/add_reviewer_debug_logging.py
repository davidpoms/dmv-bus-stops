from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text(
    encoding="utf-8"
)


# Add submit payload logging
old = """
def submit_review():

    data = request.json
"""

new = """
def submit_review():

    data = request.json

    print(
        "SUBMIT DATA:",
        data
    )
"""

if old in text and "SUBMIT DATA:" not in text:
    text = text.replace(
        old,
        new
    )
    print("Added submit payload debug logging")
else:
    print("Submit logging already exists or insertion point not found")


# Add reviewer identity logging
old = """
    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key
"""

new = """
    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    print(
        "REVIEWER:",
        reviewer_id,
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key
"""

# Only patch the submit_review occurrence by targeting nearby context
if old in text and "REVIEWER:" not in text:
    text = text.replace(
        old,
        new,
        1
    )
    print("Added reviewer identity debug logging")
else:
    print("Reviewer logging already exists or insertion point not found")


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Reviewer debug instrumentation complete"
)
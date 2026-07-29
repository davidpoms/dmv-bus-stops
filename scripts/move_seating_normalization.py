from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


insert_after = """
    data = request.json
"""


addition = """

    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )
"""


if addition.strip() not in text:

    if insert_after not in text:
        raise Exception(
            "Could not find data=request.json"
        )

    text = text.replace(
        insert_after,
        insert_after + addition,
        1
    )


# remove the later duplicate block
duplicate = """

    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )

"""

occurrences = text.count(duplicate)

if occurrences > 1:
    text = text.replace(
        duplicate,
        "",
        1
    )


p.write_text(text)

print(
    "Moved seating_type normalization"
)

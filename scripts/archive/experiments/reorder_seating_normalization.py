from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
    data = request.json


    data["shelter_type"] = (
        data.get("shelter_type")
        or data.get("shelter_protection")
        or ""
    )

    data["bench_type"] = (
        data.get("bench_type")
        or data.get("seating_type")
        or ""
    )
"""


new = """
    data = request.json


    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )


    data["shelter_type"] = (
        data.get("shelter_type")
        or data.get("shelter_protection")
        or ""
    )

    data["bench_type"] = (
        data.get("bench_type")
        or data.get("seating_type")
        or ""
    )
"""


if old not in text:
    raise Exception(
        "Could not find beginning normalization block"
    )


text = text.replace(
    old,
    new
)


# remove the later duplicate conversion

duplicate = """
    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )


"""

text = text.replace(
    duplicate,
    "",
    1
)


p.write_text(text)

print(
    "Moved seating normalization before bench_type"
)

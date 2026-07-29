from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
    if isinstance(data.get("usage_times"), list):
        data["usage_times"] = ",".join(
            data["usage_times"]
        )


    data["property_owner_outreach"] = data.get(
"""


new = """
    if isinstance(data.get("usage_times"), list):
        data["usage_times"] = ",".join(
            data["usage_times"]
        )


    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )


    data["property_owner_outreach"] = data.get(
"""


if old not in text:
    raise Exception(
        "Could not find usage_times normalization block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Updated seating_type array storage"
)

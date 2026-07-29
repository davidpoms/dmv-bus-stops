from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
    data[\"property_owner_outreach\"] = data.get(
        \"steward_interest\",
        \"\"
    )
"""

new = """
    if isinstance(data.get(\"usage_times\"), list):
        data[\"usage_times\"] = \",\".join(
            data[\"usage_times\"]
        )


    data[\"property_owner_outreach\"] = data.get(
        \"steward_interest\",
        \"\"
    )
"""

if old not in text:
    raise Exception(
        "Could not find backend normalization block"
    )

text=text.replace(old,new)

p.write_text(text)

print(
    "Updated usage_times array storage"
)

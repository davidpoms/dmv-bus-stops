from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
    data[\"shelter_type\"] = data.get(
        \"shelter_protection\",
        data.get(\"shelter_type\", \"\")
    )

    data[\"bench_type\"] = data.get(
        \"seating_type\",
        data.get(\"bench_type\", \"\")
    )

    data[\"bench_condition\"] = data.get(
        \"seating_limitations\",
        data.get(\"bench_condition\", \"\")
    )

    data[\"rider_comfort_category\"] = data.get(
        \"waiting_environment_rating\",
        data.get(\"rider_comfort_category\", \"\")
    )
"""

new = """
    data[\"shelter_type\"] = (
        data.get(\"shelter_type\")
        or data.get(\"shelter_protection\")
        or \"\"
    )

    data[\"bench_type\"] = (
        data.get(\"bench_type\")
        or data.get(\"seating_type\")
        or \"\"
    )

    data[\"bench_condition\"] = (
        data.get(\"bench_condition\")
        or data.get(\"seating_limitations\")
        or \"\"
    )

    data[\"rider_comfort_category\"] = (
        data.get(\"rider_comfort_category\")
        or data.get(\"waiting_environment_rating\")
        or \"\"
    )
"""

if old not in text:
    raise Exception("Could not find old normalization block")

text = text.replace(old, new, 1)

p.write_text(text)

print("Fixed normalization precedence using OR logic")

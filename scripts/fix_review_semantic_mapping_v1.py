from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = '''    data["shelter_type"] = (
        data.get("shelter_protection")
        or ""
    )

    data["bench_type"] = (
        data.get("seating_type")
        or ""
    )

    data["bench_condition"] = (
        data.get("seating_limitations")
        or ""
    )

    data["rider_comfort_category"] = (
        data.get("waiting_environment_rating")
        or ""
    )
'''


new = '''    # Normalize survey fields into database fields

    # Shelter type is currently not asked explicitly.
    # Keep empty unless a future shelter-type question is added.
    data["shelter_type"] = (
        data.get("shelter_type")
        or ""
    )


    # Seating characteristics
    data["bench_type"] = (
        data.get("seating_type")
        or ""
    )


    # Seating limitations / condition
    data["bench_condition"] = (
        data.get("seating_limitations")
        or ""
    )


    # Overall rider experience
    data["rider_comfort_category"] = (
        data.get("waiting_environment_rating")
        or ""
    )
'''


if old not in text:
    raise Exception(
        "Could not find semantic mapping block"
    )


text = text.replace(old, new)


p.write_text(text)

print("Fixed semantic review field mapping")

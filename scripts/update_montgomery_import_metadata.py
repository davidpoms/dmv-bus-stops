from pathlib import Path


FILE = Path(
    "scripts/import_montgomery_amenities.py"
)


text = FILE.read_text()


target = '''        match_distance_m=match["distance_m"],'''


replacement = '''        match_distance_m=match["distance_m"],
        jurisdiction="MONTGOMERY_COUNTY",
        value="yes" if present else "no",
        raw_value=str(value),'''


if target not in text:
    raise Exception(
        "Could not find match_distance_m line"
    )


text = text.replace(
    target,
    replacement,
    1
)


FILE.write_text(text)


print(
    "Updated Montgomery importer metadata fields"
)
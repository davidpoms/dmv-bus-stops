from pathlib import Path


FILE = Path("scripts/import_montgomery_amenities.py")


text = FILE.read_text()


if "raw_value=str(value)" in text:
    print("Montgomery importer already updated.")
    raise SystemExit


text = text.replace(
"""
    present = 1 if value > 0 else 0
""",
"""
    present = 1 if value > 0 else 0

    normalized_value = (
        "yes"
        if present
        else "no"
    )
"""
)


text = text.replace(
"""
        match_distance_m=match["distance_m"],
        notes=None
""",
"""
        match_distance_m=match["distance_m"],
        jurisdiction="MONTGOMERY_COUNTY",
        value=normalized_value,
        raw_value=str(value),
        notes=None
"""
)


FILE.write_text(text)

print("Updated Montgomery importer.")
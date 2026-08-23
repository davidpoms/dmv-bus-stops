from pathlib import Path


FILE = Path("src/amenities/importer.py")


text = FILE.read_text()


if "jurisdiction=None" in text:
    print("Importer already updated.")
    raise SystemExit


text = text.replace(
    "notes=None\n):",
    """notes=None,
jurisdiction=None,
value=None,
raw_value=None
):"""
)


text = text.replace(
    """
        notes
    )

    VALUES (?,?,?,?,?,?,?,?)
    """,
    """
        notes,
        jurisdiction,
        value,
        raw_value
    )

    VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """
)


text = text.replace(
    """
        match_distance_m,
        notes
    )
""",
    """
        match_distance_m,
        notes,
        jurisdiction,
        value,
        raw_value
    )
"""
)


FILE.write_text(text)

print("Updated amenity importer.")
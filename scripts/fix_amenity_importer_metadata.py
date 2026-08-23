from pathlib import Path


FILE = Path("src/amenities/importer.py")


text = FILE.read_text()


old = """
        match_distance_m,
        notes
    )

    VALUES (?,?,?,?,?,?,?,?)
"""


new = """
        match_distance_m,
        notes,
        jurisdiction,
        value,
        raw_value
    )

    VALUES (?,?,?,?,?,?,?,?,?,?,?)
"""


if old not in text:
    raise Exception(
        "Could not find insert column block"
    )


text = text.replace(
    old,
    new
)


old_values = """
        match_distance_m,
        notes
    )
)
"""


new_values = """
        match_distance_m,
        notes,
        jurisdiction,
        value,
        raw_value
    )
)
"""


if old_values not in text:
    raise Exception(
        "Could not find values block"
    )


text = text.replace(
    old_values,
    new_values
)


FILE.write_text(text)


print(
    "Updated amenity importer metadata support"
)
from pathlib import Path


FILE = Path(
    "src/amenities/importer.py"
)


text = FILE.read_text()


old_columns = """
        confidence,
        match_distance_m,
        notes
    )
"""


new_columns = """
        confidence,
        match_distance_m,
        notes,
        jurisdiction,
        value,
        raw_value
    )
"""


if old_columns not in text:
    raise Exception(
        "Could not find insert column section"
    )


text = text.replace(
    old_columns,
    new_columns,
    1
)


old_values = """
    VALUES (?,?,?,?,?,?,?,?)
"""


new_values = """
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
"""


if old_values not in text:
    raise Exception(
        "Could not find VALUES section"
    )


text = text.replace(
    old_values,
    new_values,
    1
)


old_tuple = """
        confidence,
        match_distance_m,
        notes
    )
"""


new_tuple = """
        confidence,
        match_distance_m,
        notes,
        jurisdiction,
        value,
        raw_value
    )
"""


if old_tuple not in text:
    raise Exception(
        "Could not find tuple section"
    )


text = text.replace(
    old_tuple,
    new_tuple,
    1
)


FILE.write_text(text)

print(
    "Updated amenity importer insert fields"
)
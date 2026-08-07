from pathlib import Path

path = Path("src/amenities/importer.py")

text = path.read_text()

start = text.index("def insert_amenity_evidence(")

replacement = r'''
def insert_amenity_evidence(
    db,
    physical_stop_id,
    source,
    source_record_id,
    amenity_type,
    present,
    confidence="confirmed",
    match_distance_m=None,
    notes=None,
    jurisdiction=None,
    value=None,
    raw_value=None
):

    import sqlite3

    conn = sqlite3.connect(db)

    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO stop_amenity_evidence
        (
            physical_stop_id,
            source,
            source_record_id,
            amenity_type,
            present,
            confidence,
            match_distance_m,
            notes,
            jurisdiction,
            value,
            raw_value
        )

        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            physical_stop_id,
            source,
            source_record_id,
            amenity_type,
            present,
            confidence,
            match_distance_m,
            notes,
            jurisdiction,
            value,
            raw_value
        )
    )

    conn.commit()

    inserted = cursor.rowcount

    conn.close()

    return inserted == 1
'''

path.write_text(text[:start] + replacement)

print("Rebuilt amenity importer with metadata support")
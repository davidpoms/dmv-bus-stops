import sqlite3


def insert_amenity_evidence(
    db,
    physical_stop_id,
    source,
    source_record_id,
    amenity_type,
    present,
    confidence="confirmed",
    match_distance_m=None,
    notes=None
):

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
            notes
        )

        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            physical_stop_id,
            source,
            source_record_id,
            amenity_type,
            present,
            confidence,
            match_distance_m,
            notes
        )
    )

    conn.commit()

    inserted = cursor.rowcount

    conn.close()

    return inserted == 1
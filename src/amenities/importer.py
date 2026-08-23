import sqlite3


IDENTITY_COLUMNS = (
    "physical_stop_id", "source", "source_record_id", "amenity_type"
)


def _validate_source_record_id(source, source_record_id):
    if source == "DDOT":
        raise ValueError(
            "New writes from quarantined legacy source 'DDOT' are disabled"
        )
    if source_record_id is None:
        raise ValueError(f"{source} evidence requires source_record_id")
    identity = str(source_record_id).strip()
    if not identity or identity.lower() in {"none", "null", "nan"}:
        raise ValueError(f"{source} evidence requires meaningful source_record_id")
    return identity


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
    raw_value=None,
    source_metadata=None
):
    source_record_id = _validate_source_record_id(source, source_record_id)

    conn = sqlite3.connect(db)
    cursor = upsert_amenity_evidence(
        conn,
        physical_stop_id=physical_stop_id,
        source=source,
        source_record_id=source_record_id,
        amenity_type=amenity_type,
        present=present,
        confidence=confidence,
        match_distance_m=match_distance_m,
        notes=notes,
        jurisdiction=jurisdiction,
        value=value,
        raw_value=raw_value,
        source_metadata=source_metadata,
    )
    conn.commit()
    inserted = cursor.rowcount
    conn.close()
    return inserted == 1


def upsert_amenity_evidence(
    conn,
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
    raw_value=None,
    source_metadata=None,
):
    source_record_id = _validate_source_record_id(source, source_record_id)
    return conn.execute(
        """
        INSERT INTO stop_amenity_evidence
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
            raw_value,
            source_metadata
        )

        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT
        (physical_stop_id, source, source_record_id, amenity_type)
        DO UPDATE SET
            present = excluded.present,
            confidence = excluded.confidence,
            match_distance_m = excluded.match_distance_m,
            notes = excluded.notes,
            jurisdiction = excluded.jurisdiction,
            value = excluded.value,
            raw_value = excluded.raw_value,
            source_metadata = excluded.source_metadata
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
            raw_value,
            source_metadata
        )
    )

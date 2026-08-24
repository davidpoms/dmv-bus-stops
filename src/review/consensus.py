"""
Community review consensus calculation.

Consensus is derived from community observations rather than
being manually entered. Unknown responses do not count as votes.
"""

import sqlite3
from pathlib import Path
from collections import Counter


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


def _majority(values):
    """
    Return (value, agreement) for the most common non-unknown value.

    agreement is the proportion of usable responses supporting
    the majority value.
    """

    usable = [
        value
        for value in values
        if value not in (None, "", "unknown")
    ]

    if not usable:
        return None, 0.0

    counts = Counter(usable)

    value, count = counts.most_common(1)[0]

    return value, count / len(usable)


def _yes_no(values):
    """
    Convert yes/no observation values into a boolean consensus.

    Returns:
        True, False, or None
    """

    value, agreement = _majority(values)

    if value == "yes":
        return True, agreement

    if value == "no":
        return False, agreement

    return None, 0.0


def _seating_values(rows):
    """
    Extract seating values from observations.

    Newer observations may store multiple selections as a
    comma-separated value.
    """

    values = []

    for row in rows:
        value = row["bench_type"]

        if not value:
            continue

        for item in str(value).split(","):
            item = item.strip()

            if item:
                values.append(item)

    return values


def calculate_stop_consensus(stop_id, database_path=None):
    """
    Recalculate consensus for one stop.

    Only community_review observations are considered.
    """

    conn = sqlite3.connect(database_path or DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            shelter_present,
            bench_present,
            bench_feasible,
            accessibility_status,
            bench_type,
            rider_comfort_category,
            hostile_design
        FROM stop_observations
        WHERE physical_stop_id=?
        AND source='community_review'
        ORDER BY observed_at ASC, id ASC
        """,
        (stop_id,)
    ).fetchall()

    if not rows:
        conn.execute(
            """
            DELETE FROM stop_consensus
            WHERE stop_id=?
            """,
            (stop_id,)
        )

        conn.commit()
        conn.close()

        return None

    has_shelter, shelter_agreement = _yes_no(
        [row["shelter_present"] for row in rows]
    )

    has_bench, bench_agreement = _yes_no(
        [row["bench_present"] for row in rows]
    )

    bench_feasible, feasibility_agreement = _yes_no(
        [row["bench_feasible"] for row in rows]
    )

    ada_accessible, accessibility_agreement = _yes_no(
        [
            "yes"
            if row["accessibility_status"] == "good"
            else (
                "no"
                if row["accessibility_status"] == "blocked"
                else "unknown"
            )
            for row in rows
        ]
    )

    seating_type, seating_agreement = _majority(
        _seating_values(rows)
    )

    rider_comfort, comfort_agreement = _majority(
        [
            row["rider_comfort_category"]
            for row in rows
        ]
    )

    hostile_design, hostile_agreement = _majority(
        [
            row["hostile_design"]
            for row in rows
        ]
    )

    # Only include fields that have at least one usable response.
    # Unknown / blank / unanswered fields should not count as
    # disagreement and should not artificially reduce confidence.
    agreement_pairs = [
        (
            shelter_agreement,
            [row["shelter_present"] for row in rows]
        ),
        (
            bench_agreement,
            [row["bench_present"] for row in rows]
        ),
        (
            feasibility_agreement,
            [row["bench_feasible"] for row in rows]
        ),
        (
            accessibility_agreement,
            [
                "yes"
                if row["accessibility_status"] == "good"
                else (
                    "no"
                    if row["accessibility_status"] == "blocked"
                    else "unknown"
                )
                for row in rows
            ]
        ),
        (
            seating_agreement,
            _seating_values(rows)
        ),
        (
            comfort_agreement,
            [
                row["rider_comfort_category"]
                for row in rows
            ]
        ),
        (
            hostile_agreement,
            [
                row["hostile_design"]
                for row in rows
            ]
        ),
    ]

    usable_agreements = [
        agreement
        for agreement, values in agreement_pairs
        if any(
            value not in (None, "", "unknown")
            for value in values
        )
    ]

    confidence = (
        sum(usable_agreements) / len(usable_agreements)
        if usable_agreements
        else 0.0
    )

    conn.execute(
        """
        INSERT INTO stop_consensus
        (
            stop_id,
            has_bench,
            has_shelter,
            ada_accessible,
            confidence,
            seating_type_consensus,
            rider_comfort_consensus,
            hostile_design_consensus,
            bench_feasible
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(stop_id)
        DO UPDATE SET
            has_bench=excluded.has_bench,
            has_shelter=excluded.has_shelter,
            ada_accessible=excluded.ada_accessible,
            confidence=excluded.confidence,
            seating_type_consensus=excluded.seating_type_consensus,
            rider_comfort_consensus=excluded.rider_comfort_consensus,
            hostile_design_consensus=excluded.hostile_design_consensus,
            bench_feasible=excluded.bench_feasible
        """,
        (
            stop_id,
            (
                1 if has_bench is True
                else 0 if has_bench is False
                else None
            ),
            (
                1 if has_shelter is True
                else 0 if has_shelter is False
                else None
            ),
            (
                1 if ada_accessible is True
                else 0 if ada_accessible is False
                else None
            ),
            confidence,
            seating_type,
            rider_comfort,
            hostile_design,
            (
                1
                if bench_feasible is True
                else 0
                if bench_feasible is False
                else None
            )
        )
    )

    conn.commit()

    result = conn.execute(
        """
        SELECT *
        FROM stop_consensus
        WHERE stop_id=?
        """,
        (stop_id,)
    ).fetchone()

    conn.close()

    return dict(result) if result else None

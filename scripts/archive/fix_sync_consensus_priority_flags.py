from pathlib import Path

path = Path(
    "scripts/sync_consensus_to_queue_state.py"
)

text = path.read_text()


old = """
        SET
            review_status=?,
            consensus_status=?,
            resolution_reason=?

        WHERE physical_stop_id=?
"""

new = """
        SET
            review_status=?,
            consensus_status=?,
            resolution_reason=?,
            verification_needed=?,
            community_review_available=?

        WHERE physical_stop_id=?
"""


if old not in text:
    raise Exception(
        "Could not find update block"
    )


text = text.replace(
    old,
    new
)


old_values = """
        (
            status,
            consensus_status,
            reason,
            stop_id
        )
"""


new_values = """
        (
            status,
            consensus_status,
            reason,
            0 if consensus_status == "verified" else 1,
            1,
            stop_id
        )
"""


if old_values not in text:
    raise Exception(
        "Could not find update values"
    )


text = text.replace(
    old_values,
    new_values
)


path.write_text(text)

print(
    "✓ Updated consensus sync priority flags"
)

from pathlib import Path


path = Path(
    "src/review/assignment_router.py"
)


text = path.read_text()


old = """
            LEFT JOIN stop_consensus sc
                ON sc.stop_id = rq.physical_stop_id

            WHERE
                sc.stop_id IS NULL

                OR (
                    sc.consensus_status != 'verified'
                    AND sc.reviewer_count < ?
                )
"""


new = """
            WHERE
                rq.verification_needed=1
"""


if old not in text:

    raise Exception(
        "Could not find opportunity consensus block"
    )


text = text.replace(
    old,
    new,
    1
)


path.write_text(text)


print(
    "✓ Opportunity routing now ignores verified consensus stops"
)

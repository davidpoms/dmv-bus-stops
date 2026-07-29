from pathlib import Path
import re


path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


# Fix opportunity query binding
text = re.sub(
    r"""
            LIMIT 1

            """,
            \s*
            \(
                MIN_REVIEWERS,
            \)
        \)\.fetchone\(\)
""",
    """
            LIMIT 1
            """
        ).fetchone()
""",
    text,
    count=1,
    flags=re.VERBOSE
)


# Replace route + nearby consensus filtering
pattern = r"""
        stop = cur\.execute\(
            """
            SELECT physical_stop_id
            FROM review_queue rq

            LEFT JOIN stop_consensus sc
                ON sc\.stop_id = rq\.physical_stop_id

            WHERE
                sc\.stop_id IS NULL

                OR \(
                    sc\.consensus_status != 'verified'
                    AND sc\.reviewer_count < \?
                \)

            ORDER BY RANDOM\(\)

            LIMIT 1
            """,
            \(
                MIN_REVIEWERS,
            \)
        \)\.fetchone\(\)
"""


replacement = """
        stop = cur.execute(
            \"\"\"
            SELECT physical_stop_id

            FROM review_queue

            WHERE
                community_review_available=1

            ORDER BY RANDOM()

            LIMIT 1
            \"\"\"
        ).fetchone()
"""


matches = len(
    re.findall(
        pattern,
        text,
        flags=re.VERBOSE
    )
)


print(
    "Route/nearby blocks found:",
    matches
)


if matches != 2:
    raise Exception(
        f"Expected 2 route/nearby blocks, found {matches}"
    )


text = re.sub(
    pattern,
    replacement,
    text,
    flags=re.VERBOSE
)


path.write_text(text)


print(
    "✓ Cleaned assignment router review modes"
)

from pathlib import Path

p = Path("scripts/rebuild_stop_consensus.py")

text = p.read_text()

text = text.replace(
"""HAVING COUNT(
    DISTINCT COALESCE(reviewer_id, observer, id)
) >= 3""",
"""HAVING COUNT(*) >= 1"""
)

text = text.replace(
"""SELECT

            bench_present,
            bench_feasible,
            concrete_pad_needed,
            ada_clearance_possible,
            confidence""",
"""SELECT

            bench_present,
            bench_feasible,
            concrete_pad_needed,
            ada_clearance_possible,
            confidence,
            reviewer_id"""
)


text = text.replace(
"""count = len(rows)""",
"""count = len(set(
        r[5]
        for r in rows
        if r[5] is not None
    ))"""
)


text = text.replace(
"""FROM stop_observations

        WHERE physical_stop_id=?""",
"""FROM stop_observations

        WHERE physical_stop_id=?

        AND (
            observer IS NULL
            OR observer NOT LIKE 'test%'
        )"""
)


text = text.replace(
"""WHERE

    observer IS NULL
    OR observer NOT LIKE 'test%'

GROUP BY physical_stop_id""",
"""WHERE

    observer IS NULL
    OR observer NOT LIKE 'test%'

GROUP BY physical_stop_id"""
)


p.write_text(text)

print("Updated rebuild_stop_consensus.py")

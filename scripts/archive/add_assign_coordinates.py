from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text()

text = text.replace(
'''def assign_stop(
    reviewer_id,
    scenario,
    stop_id=None
):''',
'''def assign_stop(
    reviewer_id,
    scenario,
    stop_id=None,
    latitude=None,
    longitude=None
):'''
)

old = '''
        ORDER BY rq.priority_rank
        LIMIT 1
        """
        ).fetchone()
'''

new = '''
        ORDER BY
            (
                (ps.latitude - ?) * (ps.latitude - ?)
                +
                (ps.longitude - ?) * (ps.longitude - ?)
            )
        LIMIT 1
        """,
        (
            latitude,
            latitude,
            longitude,
            longitude
        )
        ).fetchone()
'''

# Only replace the nearby block occurrence
text = text.replace(old, new, 1)

path.write_text(text)

print("Added coordinate-aware nearby assignment")

from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text()

old = '''
            WHERE rq.community_review_available=1
            ORDER BY rq.priority_rank
            LIMIT 1
'''

new = '''
            WHERE rq.community_review_available=1
            ORDER BY
                CASE
                    WHEN ? IS NOT NULL AND ? IS NOT NULL THEN
                        (
                            (ps.latitude - ?) * (ps.latitude - ?)
                            +
                            (ps.longitude - ?) * (ps.longitude - ?)
                        )
                    ELSE rq.priority_rank
                END
            LIMIT 1
'''

if old not in text:
    raise Exception("Could not find nearby query")

text = text.replace(old, new, 1)

# add query parameters after the fetch
old2 = '''
        ).fetchone()
'''

new2 = '''
        ,
        (
            latitude,
            longitude,
            latitude,
            latitude,
            longitude,
            longitude
        )
        ).fetchone()
'''

# Only replace the first fetch after nearby query
start = text.index('elif scenario == "nearby"')
end = text.index('elif scenario == "route"')

section = text[start:end]

if old2 not in section:
    raise Exception("Could not find nearby fetch")

section = section.replace(old2, new2, 1)

text = text[:start] + section + text[end:]

path.write_text(text)

print("Fixed nearby distance query")

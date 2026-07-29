from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''
    review_count = query_db(
        """
        SELECT COUNT(*)
        FROM stop_reviews
        WHERE stop_id = ?
        """,
        (stop_id,)
    )[0][0]
'''

new = '''
    review_count = query_db(
        """
        SELECT COUNT(*)
        FROM stop_observations
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )[0][0]
'''

if old not in text:
    print("Target block not found")
    raise SystemExit(1)

text = text.replace(old, new)

p.write_text(text)

print("Migrated community-status review count to stop_observations")

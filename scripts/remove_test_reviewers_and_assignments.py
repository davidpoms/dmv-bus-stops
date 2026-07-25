import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Remove placeholder reviews if any slipped back in
cur.execute("""
DELETE FROM stop_reviews
WHERE reviewer_id LIKE 'test%'
   OR reviewer_id LIKE 'fake%'
   OR anonymous_email LIKE '%test%'
   OR anonymous_email LIKE '%fake%'
""")

reviews_removed = cur.rowcount

# Remove test assignments
cur.execute("""
DELETE FROM stop_review_assignments
WHERE reviewer_id IN (
    SELECT id
    FROM community_reviewers
    WHERE reviewer_key LIKE 'test%'
       OR reviewer_key LIKE 'fake%'
)
""")

assignments_removed = cur.rowcount

# Remove test reviewers
cur.execute("""
DELETE FROM community_reviewers
WHERE reviewer_key LIKE 'test%'
   OR reviewer_key LIKE 'fake%'
""")

reviewers_removed = cur.rowcount

conn.commit()

print(f"Reviews removed: {reviews_removed}")
print(f"Assignments removed: {assignments_removed}")
print(f"Reviewers removed: {reviewers_removed}")

conn.close()

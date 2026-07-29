from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

text = text.replace(
"""
FROM stop_reviews
GROUP BY stop_id
HAVING COUNT(*) >= 3
""",
"""
FROM stop_consensus
WHERE consensus_status='verified'
"""
)

p.write_text(text)

print("Updated route validation to use consensus table")

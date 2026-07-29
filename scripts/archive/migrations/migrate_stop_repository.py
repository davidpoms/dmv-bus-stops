from pathlib import Path

p = Path("src/database/stop_repository.py")

text = p.read_text()

text = text.replace(
    "FROM stop_reviews",
    "FROM stop_observations"
)

text = text.replace(
    "WHERE stop_id = ?",
    "WHERE physical_stop_id = ?"
)

text = text.replace(
    """
        Retrieve reviews
        for a stop.
""",
    """
        Retrieve observations
        for a stop.
"""
)

p.write_text(text)

print("Migrated StopRepository to stop_observations")

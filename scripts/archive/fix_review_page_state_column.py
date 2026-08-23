from pathlib import Path

app = Path("src/api/app.py")
text = app.read_text(encoding="utf-8")

# Replace jurisdiction with state in review_page query
text = text.replace(
"""        SELECT
            id,
            primary_name,
            latitude,
            longitude,
            jurisdiction
        FROM physical_stops
        WHERE id=?
""",
"""        SELECT
            id,
            primary_name,
            latitude,
            longitude,
            state
        FROM physical_stops
        WHERE id=?
"""
)

# Remove obsolete MD/VA normalization block
old = """    stop_row = list(stop[0])

    # Normalize displayed jurisdiction from state field
    if stop_row[4] == "MD/VA":
        stop_row[4] = "Maryland / Virginia"
"""

if old in text:
    text = text.replace(
        old,
        """    stop_row = list(stop[0])
"""
    )
    print("Removed MD/VA normalization.")
else:
    print("Normalization block already gone.")

app.write_text(text, encoding="utf-8")

print("review_page updated.")
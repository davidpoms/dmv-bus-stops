from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
    """
            p.state,
            p.dc_ward,
""",
    """
            p.jurisdiction,
            p.dc_ward,
"""
)

text = text.replace(
    """
            "state": row[4],
            "ward": row[5],
""",
    """
            "state": row[4],
            "jurisdiction": row[4],
            "ward": row[5],
"""
)

p.write_text(text)

print("Updated review info endpoint to use jurisdiction")

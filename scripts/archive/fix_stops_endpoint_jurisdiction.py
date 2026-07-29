from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
    """
            p.state,
            p.dc_ward,
            p.dc_anc,
""",
    """
            p.jurisdiction,
            p.dc_ward,
            p.dc_anc,
"""
)

text = text.replace(
    """
            "state": row[4],
            "ward": row[5],
            "anc": row[6],
""",
    """
            "state": row[4],
            "jurisdiction": row[4],
            "ward": row[5],
            "anc": row[6],
"""
)

p.write_text(text)

print("Fixed /stops endpoint jurisdiction")

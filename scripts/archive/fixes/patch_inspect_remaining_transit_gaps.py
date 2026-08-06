from pathlib import Path

target = Path("scripts/inspect_remaining_transit_gaps.py")

text = target.read_text()

# Add helper after cursor creation
if "def dump(rows):" not in text:
    text = text.replace(
        "c = conn.cursor()\n",
        """c = conn.cursor()


def dump(rows):
    for row in rows:
        print(dict(row))
"""
    )

# Replace print(fetchall()) patterns
text = text.replace(
    "print(c.execute(",
    "dump(c.execute("
)

text = text.replace(
    ")).fetchall())",
    ")).fetchall())"
)

target.write_text(text)

print("Patched:", target)
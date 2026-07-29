from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

# Find the second occurrence of the impact filter section
marker = """AND (
                ? IS NULL
                OR (
                    ? = 'high'
                    AND sii.impact_level IN ('high', 'very_high')
                )
                OR (
                    ? = 'very_high'
                    AND sii.impact_level = 'very_high'
                )
            )"""

count = text.count(marker)

print("impact filter blocks found:", count)

if count < 2:
    print("Need two filter blocks, stopping")
    exit(1)

# The first is already fixed in the route branch.
# Add the missing parameters to the second branch.
old = """
            ORDER BY sii.opportunity_score DESC;
            """,
        )

    return jsonify"""

new = """
            ORDER BY sii.opportunity_score DESC;
            """,
            (
                impact,
                impact,
                impact
            )
        )

    return jsonify"""

if old not in text:
    print("Parameter location not found")
    exit(1)

text = text.replace(old, new, 1)

p.write_text(text)

print("Global impact filter parameters patched")

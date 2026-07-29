from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
    '    impact = request.args.get("impact")',
    '    impact = request.args.get("impact")\n\n    priority = request.args.get("priority")'
)

# Add priority filtering to both SQL branches
old = """
            ORDER BY sii.opportunity_score DESC;
"""

new = """
            AND (
                ? IS NULL
                OR sii.priority_level = ?
            )

            ORDER BY sii.opportunity_score DESC;
"""

# Only replace the two map query endings
text = text.replace(old, new, 2)

# Add parameters to existing query tuples
text = text.replace(
"""                impact,
                impact,
                impact,
                impact
            )""",
"""                impact,
                impact,
                impact,
                impact,
                priority,
                priority
            )"""
)

text = text.replace(
"""                impact,
                impact,
                impact
            )""",
"""                impact,
                impact,
                impact,
                priority,
                priority
            )"""
)

p.write_text(text)

print("Added priority filtering support")

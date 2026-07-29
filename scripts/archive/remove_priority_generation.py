from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

text = text.replace(
"""        impact_list=impact_list,
        priority_rows=priority_rows
""",
"""
"""
)

p.write_text(text)

print("Removed priority template substitutions")

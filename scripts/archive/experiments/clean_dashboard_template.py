from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


remove_sections = [
"""
<label>
Impact Filter:
</label>
""",

"""
<label>
Priority Filter:
</label>
""",

"""
<select id="prioritySelect">
""",

"""
<select id="impactSelect">
""",

"""
<div id="prioritySummary">
""",

"""
<div id="topPriorities">
""",

"""
<h2>
Project Status
</h2>
""",

"""
<h2>
Impact Levels
</h2>
""",

"""
<h2>
Top Priority Stops
</h2>
"""
]


for section in remove_sections:
    text = text.replace(section, "")


p.write_text(text)

print("Cleaned dashboard template")

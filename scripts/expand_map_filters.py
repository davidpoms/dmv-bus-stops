from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

old = """
<label>
Ward
<select id="wardFilter">
<option value="">All</option>
</select>
</label>
"""

new = """
<label>
Ward
<select id="wardFilter">
<option value="">All</option>
</select>
</label>


<label>
ANC
<select id="ancFilter">
<option value="">All</option>
</select>
</label>


<label>
Municipality
<select id="municipalityFilter">
<option value="">All</option>
</select>
</label>
"""

if old not in text:
    raise Exception("Ward filter block not found")

text = text.replace(old,new)

p.write_text(text)

print("Added ANC and municipality filters")

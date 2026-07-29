from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = """
<select id="impactSelect">
"""

insert = """
<label>
Priority Filter:
</label>

<select id="prioritySelect">

<option value="">
All Priorities
</option>

<option value="P1">
P1 Immediate
</option>

<option value="P2">
P2 High Value
</option>

<option value="P3">
P3 Candidate
</option>

<option value="monitor">
Monitor
</option>

</select>

"""

if marker in text:
    text = text.replace(marker, insert + marker, 1)
    p.write_text(text)
    print("Added priority dropdown")
else:
    print("Impact selector not found")

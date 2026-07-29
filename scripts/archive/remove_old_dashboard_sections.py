from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

remove_blocks = [
"""
<ul>
$impact_list
</ul>
""",

"""
<table>

<tr>
<th>Rank</th>
<th>Stop</th>
<th>Location</th>
<th>Score</th>
<th>Impact</th>
</tr>

$priority_rows

</table>
"""
]

for block in remove_blocks:
    text = text.replace(block, "")

p.write_text(text)

print("Removed old priority/impact dashboard sections")

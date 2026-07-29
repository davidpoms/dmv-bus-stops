from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

old = """
<div class="card">
<h2>$total_projects</h2>
<p>Active Projects</p>
</div>
"""

new = """
<div class="card">
<h2>Community Review Network</h2>

<p>
Stops identified:
2,621
</p>

<p>
Help validate where riders need better waiting conditions.
</p>

</div>
"""

if old not in text:
    print("active projects card not found")
else:
    text = text.replace(old,new)
    p.write_text(text)
    print("active projects card replaced")


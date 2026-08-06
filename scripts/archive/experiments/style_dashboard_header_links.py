from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

old = """
<div class="dashboard-links">

<a href="/handbook">
📘 Community Handbook
</a>


<a href="/volunteer-handbook">
🤝 Volunteer Handbook
</a>

</div>
"""


new = """
<div class="dashboard-links">

<a href="/handbook" class="dashboard-button">
📘 Community Handbook
</a>


<a href="/volunteer-handbook" class="dashboard-button">
🤝 Volunteer Handbook
</a>

</div>
"""


if old not in text:
    raise SystemExit("Dashboard links block not found")


text = text.replace(old,new)

p.write_text(text)

print("Styled handbook links")

from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


marker = """
<h2>
Live Priority Map
</h2>
"""


insert = """
<div class="card">

<h2>
How do you want to help?
</h2>

<p>
Stops move from community review to bench candidate only after neighbors validate the need.
</p>


<button onclick="loadVolunteerMode('opportunity')">
⭐ Review highest-opportunity stops
</button>


<button onclick="loadVolunteerMode('route')">
🚌 Review my route
</button>


<button onclick="loadVolunteerMode('nearby')">
📍 Review stops near me
</button>


</div>

"""


if marker not in text:
    print("dashboard map marker not found")
    raise SystemExit(1)


text = text.replace(
    marker,
    insert + marker
)


p.write_text(text)

print("volunteer action panel added")


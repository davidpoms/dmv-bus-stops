from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


marker = """
<h2>
Live Priority Map
</h2>
"""


if marker not in text:
    raise SystemExit("Live Priority Map heading not found")


insert = """
<div class="card map-guide">

<h2>
Explore Transit Improvement Opportunities
</h2>

<p>
Use the map to explore stops that may benefit from better waiting conditions.
Different review paths help you find the stops that matter most:
</p>


<ul>

<li>
<strong>⭐ Highest Opportunity Stops</strong>
<br>
Review locations where available evidence suggests the greatest potential impact.
</li>


<li>
<strong>🚌 My Routes</strong>
<br>
Focus on routes you ride, use, or know well.
</li>


<li>
<strong>📍 Near Me</strong>
<br>
Find nearby stops where community input can help guide future improvements.
</li>


</ul>


<p>
Community reviews add local knowledge to help prioritize improvements.
</p>

</div>


"""


text = text.replace(
    marker,
    insert + marker,
    1
)


p.write_text(text)

print("Added map explanation card")

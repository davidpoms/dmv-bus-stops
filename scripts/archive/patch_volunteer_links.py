from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


text = text.replace(
"""
<button onclick="loadVolunteerMode('opportunity')">
⭐ Review highest-opportunity stops
</button>


<button onclick="loadVolunteerMode('route')">
🚌 Review my route
</button>


<button onclick="loadVolunteerMode('nearby')">
📍 Review stops near me
</button>
""",
"""
<a href="/dashboard?review=opportunity"
class="volunteerLink">

⭐ Highest Opportunity Stops

<p>
Review stops where community validation could unlock the most impact.
</p>

Start reviewing →
</a>


<a href="/dashboard?review=route"
class="volunteerLink">

🚌 My Routes

<p>
Review stops along routes you ride or steward.
</p>

Choose a route →
</a>


<a href="/dashboard?review=nearby"
class="volunteerLink">

📍 Near Me

<p>
Find stops close to you needing community review.
</p>

Find nearby stops →
</a>
"""
)


p.write_text(text)

print("volunteer links patched")


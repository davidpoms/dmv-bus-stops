from pathlib import Path
import re

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


# -------------------------------------------------
# Replace volunteer section
# -------------------------------------------------

start = text.find('<div class="card volunteer-card">')

end = text.find(
    '<h2>\nLive Priority Map'
)

if start == -1:
    raise SystemExit("Volunteer card start not found")

if end == -1:
    raise SystemExit("Live Priority Map heading not found")


new_volunteer = """
<div class="card volunteer-card">

<h2>
How do you want to help?
</h2>

<p>
Community review helps identify where riders would benefit most from better waiting conditions.
Choose a review path based on how you want to explore stops.
</p>


<h3>
⭐ Highest Opportunity Stops
</h3>

<a href="/dashboard?review=opportunity"
class="volunteerLink">
Start reviewing highest opportunity stops →
</a>

<p>
Review locations where available evidence suggests the greatest potential impact from transit improvements.
</p>


<h3>
🚌 My Routes
</h3>

<a href="/dashboard?review=route"
class="volunteerLink">
Choose a route →
</a>

<p>
Focus on stops along routes you ride, use, or know well.
</p>


<h3>
📍 Near Me
</h3>

<a href="/dashboard?review=nearby"
class="volunteerLink">
Find nearby stops →
</a>

<p>
Find stops near your location where community input can help guide future improvements.
</p>


</div>


"""


text = text[:start] + new_volunteer + text[end:]


# -------------------------------------------------
# Remove geography overview section if still present
# -------------------------------------------------

geo_start = text.find(
    "<h2>\nGeography Overview\n</h2>"
)

pipeline_start = text.find(
    "<h2>\nReview Pipeline Coverage\n</h2>"
)

if geo_start != -1 and pipeline_start != -1:

    text = (
        text[:geo_start]
        + text[pipeline_start:]
    )

    print("Removed Geography Overview tables")


# -------------------------------------------------
# Ensure no old review queue heading remains
# -------------------------------------------------

text = re.sub(
    r'<h2>\s*Community Review Queue\s*</h2>\s*<div id="reviewQueue">.*?</div>',
    '',
    text,
    flags=re.S
)


p.write_text(text)

print("Dashboard volunteer layout finalized")

from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


# Find volunteer card
start = text.find('<div class="card volunteer-card">')

if start == -1:
    raise SystemExit("Volunteer card not found")


# Find next major section after volunteer card
end = text.find("Live Priority Map", start)

if end == -1:
    raise SystemExit("Could not find Live Priority Map")


# Move backward to include its heading tag
end = text.rfind("<h2>", start, end) 

if end == -1:
    raise SystemExit("Could not find map heading start")


new_section = """
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

<a href="/dashboard?review=opportunity" class="volunteerLink">
Start reviewing highest opportunity stops →
</a>

<p>
Review locations where available evidence suggests the greatest potential impact from transit improvements.
</p>


<h3>
🚌 My Routes
</h3>

<a href="/dashboard?review=route" class="volunteerLink">
Choose a route →
</a>

<p>
Focus on stops along routes you ride, use, or know well.
</p>


<h3>
📍 Near Me
</h3>

<a href="/dashboard?review=nearby" class="volunteerLink">
Find nearby stops →
</a>

<p>
Find stops near your location where community input can help guide future improvements.
</p>


</div>


"""


text = text[:start] + new_section + text[end:]

p.write_text(text)

print("Volunteer card replaced")

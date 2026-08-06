from pathlib import Path

p=Path("src/dashboard/templates/dashboard.html")

text=p.read_text()


start=text.find('<div class="card volunteer-card">')

end=text.find('<h2>\nLive Priority Map', start)


if start==-1 or end==-1:
    raise Exception("Volunteer boundaries not found")


new="""
<div class="card volunteer-card">

<h2>
How do you want to help?
</h2>


<p>
Community review helps identify where riders would benefit most from better waiting conditions.
Choose a review path:
</p>


<div class="review-options">


<div class="review-option">

<h3>
⭐ Highest Opportunity Stops
</h3>

<a href="/dashboard?review=opportunity">
Start reviewing →
</a>

<p>
Review locations where available evidence suggests the greatest potential improvement.
</p>

</div>



<div class="review-option">

<h3>
🚌 My Routes
</h3>

<a href="/dashboard?review=route">
Choose a route →
</a>

<p>
Review stops along routes you ride, use, or steward.
</p>

</div>



<div class="review-option">

<h3>
📍 Near Me
</h3>

<a href="/dashboard?review=nearby">
Find nearby stops →
</a>

<p>
Find stops near your location that need community validation.
</p>

</div>


</div>

</div>


"""


text=text[:start]+new+text[end:]

p.write_text(text)

print("Volunteer card rebuilt")

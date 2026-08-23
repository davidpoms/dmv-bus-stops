from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


start = text.find('<div class="card volunteer-card">')

if start == -1:
    raise SystemExit("Volunteer card not found")


end = text.find("</div>", start)

# account for nested help-options div
end = text.find("</div>", end + 6) + 6


replacement = """
<div class="card volunteer-card">

<h2>
How do you want to help?
</h2>


<p>
Community review helps identify where riders would benefit most from better waiting conditions.
Choose a review path below.
</p>


<div class="review-options">


<div class="review-option">

<a href="/dashboard?review=opportunity">
⭐ Highest Opportunity Stops
</a>

<p>
Review stops where available evidence suggests the greatest potential improvement.
</p>

</div>



<div class="review-option">

<a href="/dashboard?review=route">
🚌 My Routes
</a>

<p>
Review stops along routes you ride, use, or steward.
</p>

</div>



<div class="review-option">

<a href="/dashboard?review=nearby">
📍 Near Me
</a>

<p>
Find stops near your current location that need community validation.
</p>

</div>


</div>

</div>

"""


text = text[:start] + replacement + text[end:]


p.write_text(text)

print("Rebuilt volunteer card")

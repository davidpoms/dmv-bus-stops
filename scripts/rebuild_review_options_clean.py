from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text(encoding="utf-8")


start = text.find('<div class="review-options">')
end = text.find('<div class="card map-filter-card">')


if start == -1:
    raise Exception("Could not find review-options start")

if end == -1:
    raise Exception("Could not find map filter card")


replacement = """
<div class="review-options">


<div class="review-option">

<a href="/review/routes">
🚌 Choose My Routes
</a>

<p>
Select the routes you ride or steward so reviews can prioritize those stops.
</p>

</div>


<div class="review-option">

<a href="/review/start?mode=route">
🚌 My Routes
</a>

<p>
Review stops along your selected routes.
</p>

</div>


<div class="review-option">

<a href="/review/start?mode=opportunity">
⭐ Priority Verification Stops
</a>

<p>
Review stops where additional community verification would provide the most value.
</p>

</div>


<div class="review-option">

<a href="#"
id="nearbyReviewLink">
📍 Near Me
</a>

<p>
Find stops near your current location that need community validation.
</p>

</div>


</div>


"""


text = text[:start] + replacement + text[end:]


path.write_text(
    text,
    encoding="utf-8"
)


print("Rebuilt volunteer review options cleanly")
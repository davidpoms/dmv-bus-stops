from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text(encoding="utf-8")


start_marker = '<div class="review-options">'
end_marker = '<div class="card map-filter-card">'


start = text.find(start_marker)
end = text.find(end_marker)


if start == -1 or end == -1:
    raise Exception("Could not locate volunteer section")


new_section = """
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


text = (
    text[:start]
    + new_section
    + text[end:]
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Rebuilt volunteer review options")
from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text()


# -------------------------------------------------
# Remove duplicate "Help Verify Transit Improvements"
# -------------------------------------------------

start = text.find("<h3>Help Verify Transit Improvements</h3>")

if start != -1:

    card_start = text.rfind('<div id="validationPanel">', 0, start)

    if card_start != -1:

        card_end = text.find("</div>", start)

        # close validationList div
        card_end = text.find("</div>", card_end + 6) + 6

        text = (
            text[:card_start]
            +
            text[card_end:]
        )

        print("Removed Help Verify box")



# -------------------------------------------------
# Remove duplicate bottom Community Review Queue
# -------------------------------------------------

queue_positions = []

idx = 0
while True:
    idx = text.find('<div id="reviewQueue">', idx)

    if idx == -1:
        break

    queue_positions.append(idx)
    idx += 1


# Keep the reviewQueue inside modal, remove later one

if len(queue_positions) > 1:

    start = queue_positions[-1]

    card_start = text.rfind("<h2>", 0, start)

    if card_start != -1:

        end = text.find("</div>", start)

        end = text.find("</div>", end + 6) + 6

        text = (
            text[:card_start]
            +
            text[end:]
        )

        print("Removed duplicate review queue")



# -------------------------------------------------
# Replace volunteer section with expanded card
# -------------------------------------------------

old_start = text.find(
    '<div class="card">\n\n<h2>\nHow do you want to help?'
)

if old_start == -1:

    old_start = text.find(
        "<h2>\nHow do you want to help?"
    )


if old_start != -1:

    card_start = text.rfind(
        '<div class="card">',
        0,
        old_start
    )

    next_section = text.find(
        "<h2>\nLive Priority Map",
        old_start
    )

    if next_section != -1:

        replacement = """
<div class="card volunteer-card">

<h2>
How do you want to help?
</h2>


<p>
Community review helps identify where riders would benefit most from better waiting conditions.
Choose the type of stop you want to review:
</p>


<div class="help-options">


<a href="/dashboard?review=opportunity"
class="volunteerLink">

⭐ Highest Opportunity Stops

<p>
Review locations where available evidence suggests the greatest potential improvement.
</p>

Start reviewing →
</a>


<a href="/dashboard?review=route"
class="volunteerLink">

🚌 My Routes

<p>
Review stops along routes you ride, use, or steward.
</p>

Choose a route →
</a>


<a href="/dashboard?review=nearby"
class="volunteerLink">

📍 Near Me

<p>
Find stops near your current location that need community validation.
</p>

Find nearby stops →
</a>


</div>

</div>


"""

        text = (
            text[:card_start]
            +
            replacement
            +
            text[next_section:]
        )

        print("Expanded volunteer help section")



path.write_text(text)

print("Dashboard layout refinement complete")

from pathlib import Path
import re

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


# -------------------------------------------------
# Remove duplicate map guide card
# -------------------------------------------------

match = re.search(
    r'<div class="card map-guide">.*?</div>\s*</div>',
    text,
    flags=re.S
)

if match:
    text = text[:match.start()] + text[match.end():]
    print("Removed duplicate map guide card")



# -------------------------------------------------
# Replace volunteer section
# -------------------------------------------------

start = text.find('<div class="card volunteer-card">')

if start != -1:

    map_match = re.search(
        r'<h2>\s*Live Priority Map\s*</h2>',
        text[start:],
        flags=re.S
    )

    if map_match:

        end = start + map_match.start()

        replacement = """
<div class="card volunteer-card">

<h2>
How do you want to help?
</h2>


<p>
Choose a review path. Each option helps identify where transit improvements could have the greatest benefit.
</p>


<div class="help-options">


<div class="help-option">

<a href="/dashboard?review=opportunity">
⭐ Highest Opportunity Stops
</a>

<p>
Review stops where available evidence suggests the greatest potential improvement.
</p>

</div>


<div class="help-option">

<a href="/dashboard?review=route">
🚌 My Routes
</a>

<p>
Review stops along routes you ride, use, or know well.
</p>

</div>


<div class="help-option">

<a href="/dashboard?review=nearby">
📍 Near Me
</a>

<p>
Find nearby stops where community input can help guide improvements.
</p>

</div>


</div>

</div>


"""

        text = text[:start] + replacement + text[end:]

        print("Rebuilt volunteer card")

    else:
        print("Map heading not found")

else:
    print("Volunteer card not found")



# -------------------------------------------------
# Remove Geography Overview
# -------------------------------------------------

geo_start = re.search(
    r'<h2>\s*Geography Overview\s*</h2>',
    text,
    flags=re.S
)

pipeline_start = re.search(
    r'<h2>\s*Review Pipeline Coverage\s*</h2>',
    text,
    flags=re.S
)


if geo_start and pipeline_start:

    text = (
        text[:geo_start.start()]
        +
        text[pipeline_start.start():]
    )

    print("Removed Geography Overview section")

else:
    print("Could not find geography boundaries")



p.write_text(text)

print("Dashboard cleanup complete")

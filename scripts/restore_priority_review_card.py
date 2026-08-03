from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text(encoding="utf-8")


old = """
<div class="review-option">

<a href="/review/start?mode=opportunity">
â Near Me
</a>

<p>
Find stops near your current location that need community validation.
</p>

</div>
"""


new = """
<div class="review-option">

<a href="/review/start?mode=opportunity">
⭐ Priority Verification Stops
</a>

<p>
Review stops where additional community verification would provide the most value.
</p>

</div>


<div class="review-option">

<a href="/review/start?mode=nearby">
📍 Near Me
</a>

<p>
Find stops near your current location that need community validation.
</p>

</div>
"""


if old in text:
    text = text.replace(old, new, 1)
    print("Restored priority card and fixed Near Me mode")
else:
    print("Exact block not found. Searching by URL instead.")

    start = text.find('<a href="/review/start?mode=opportunity">')

    if start != -1:
        block_start = text.rfind("<div class=\"review-option\">", 0, start)
        block_end = text.find("</div>", text.find("</p>", start)) + len("</div>")

        replacement = new

        text = (
            text[:block_start]
            + replacement
            + text[block_end:]
        )

        print("Replaced opportunity card using URL match")

    else:
        print("Could not find opportunity link")


path.write_text(
    text,
    encoding="utf-8"
)
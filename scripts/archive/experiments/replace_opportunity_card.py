from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text(encoding="utf-8")


old_start = '<a href="/review/start?mode=opportunity">'

start = text.find(old_start)

if start == -1:
    raise Exception("Opportunity card not found")


card_start = text.rfind('<div class="review-option">', 0, start)

card_end = text.find('</div>', text.find('</p>', start))

card_end = text.find('</div>', card_end + 6) + len('</div>')


replacement = """
<div class="review-option">

<a href="/review/start?mode=opportunity">
⭐ Priority Verification Stops
</a>

<p>
Review stops where additional community verification would provide the most value.
</p>

</div>
"""


text = (
    text[:card_start]
    + replacement
    + text[card_end:]
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Replaced opportunity card")
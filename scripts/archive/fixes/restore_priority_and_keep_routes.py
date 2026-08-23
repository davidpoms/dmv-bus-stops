from pathlib import Path

dashboard = Path("src/dashboard/templates/dashboard.html")

text = dashboard.read_text(encoding="utf-8")


priority_card = """
<div class="review-option">

<a href="/review/start?mode=opportunity">
⭐ Priority Verification Stops
</a>

<p>
Review stops where additional community verification would provide the most value.
</p>

</div>


"""


route_card_marker = """
<div class="review-option">

<a href="/review/routes">
🚌 Choose My Routes
</a>
"""


if "⭐ Priority Verification Stops" in text:
    print("Priority card already exists. No change needed.")
    exit()


if route_card_marker not in text:
    print("Could not find Choose My Routes card.")
    exit()


text = text.replace(
    route_card_marker,
    priority_card + route_card_marker,
    1
)


dashboard.write_text(
    text,
    encoding="utf-8"
)

print("Restored Priority Verification card.")
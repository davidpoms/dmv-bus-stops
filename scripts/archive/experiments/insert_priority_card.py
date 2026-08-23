from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text(encoding="utf-8")


marker = """
<div class="review-option">

<a href="/review/start?mode=opportunity">
â Near Me
</a>
"""


priority = """
<div class="review-option">

<a href="/review/start?mode=opportunity">
⭐ Priority Verification Stops
</a>

<p>
Review stops where additional community verification would provide the most value.
</p>

</div>


"""


if "Priority Verification Stops" in text:
    print("Priority card already exists.")
    exit()


if marker not in text:
    print("Could not find Near Me card marker.")
    exit()


text = text.replace(
    marker,
    priority + marker,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Inserted Priority Verification card.")
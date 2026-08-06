from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text(encoding="utf-8")


near_me_block = """
<div class="review-option">

<a href="/review/start?mode=opportunity">
â Near Me
</a>

<p>
Find stops near your current location that need community validation.
</p>

</div>
"""


priority_block = """
<div class="review-option">

<a href="/review/start?mode=opportunity">
⭐ Priority Verification Stops
</a>

<p>
Review stops where additional community verification would provide the most value.
</p>

</div>


"""


if priority_block.strip() in text:
    print("Priority card already present in this exact format.")
    exit()


if near_me_block not in text:
    print("Could not find Near Me block.")
    exit()


text = text.replace(
    near_me_block,
    priority_block + near_me_block,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Inserted Priority Verification card before Near Me.")
from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")

needle = """
<input type="hidden"
name="review_action"
id="review_action"
value="new">
"""

replacement = """
<input type="hidden"
name="review_action"
id="review_action"
value="new">


<div class="panel volunteer-identity-card">

<h3>
Optional: get credit for your review
</h3>

<p>
Choose a display name to show on your community contributions.
You can leave this blank and remain anonymous.
</p>

<label>
Display name
</label>

<input
type="text"
name="display_name"
placeholder="Example: Metro Mapper"
>

</div>
"""

if needle not in text:
    raise SystemExit("Could not find review action block")

text = text.replace(
    needle,
    replacement
)

path.write_text(
    text,
    encoding="utf-8"
)

print("Added display name field")
from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")

old = """
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

{% if reviewer_name %}

<p>
Continue as <strong>{{ reviewer_name }}</strong>
</p>

<label>
Change display name (optional)
</label>

<input
type="text"
name="display_name"
placeholder="Leave blank to continue as {{ reviewer_name }}"
>

<p>
You can also submit anonymously.
</p>

{% else %}
"""

new = """
<h3>
Optional: get credit for your review
</h3>


{% if reviewer_name %}

<p>
Welcome back <strong>{{ reviewer_name }}</strong>!
</p>

<p>
Your reviews will be credited to this community profile.
</p>

<label>
Change display name (optional)
</label>

<input
type="text"
name="display_name"
placeholder="Leave blank to continue as {{ reviewer_name }}"
>

<p>
You can also submit anonymously.
</p>


{% else %}

<p>
Choose a display name to show on your community contributions.
You can leave this blank and remain anonymous.
</p>

<label>
Display name
</label>
"""

if old not in text:
    raise SystemExit("identity block not found")

text = text.replace(
    old,
    new
)

path.write_text(
    text,
    encoding="utf-8"
)

print("Cleaned reviewer identity card")
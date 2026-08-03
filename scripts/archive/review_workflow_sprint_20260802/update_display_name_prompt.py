from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


old = """
<input
type="text"
name="display_name"
placeholder="Example: Metro Mapper"
>
"""

new = """
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

<input
type="text"
name="display_name"
placeholder="Example: Metro Mapper"
>

{% endif %}
"""


if old not in text:
    raise SystemExit("display name field not found")


text=text.replace(
    old,
    new
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Updated display name prompt")
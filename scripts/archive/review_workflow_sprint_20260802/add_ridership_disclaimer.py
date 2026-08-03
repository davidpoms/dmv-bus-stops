from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


target = """
</div>


${
    result.reviewer_stats.first_review
"""


replacement = """
<p class="impact-note">
Ridership figures represent route-level weekday boardings associated with
routes serving reviewed stops. They do not represent unique riders or
stop-level boardings.
</p>


</div>


${
    result.reviewer_stats.first_review
"""


if target not in text:
    raise Exception("Impact note insertion point not found")


text = text.replace(
    target,
    replacement,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Added ridership clarification")
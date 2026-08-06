from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text(encoding="utf-8")


duplicate = """
<div class="review-option">

<a href="/review/start?mode=route">
🚌 My Routes
</a>

<p>
Review stops along routes you ride, use, or steward.
</p>

</div>
"""


if duplicate in text:
    text = text.replace(
        duplicate,
        "",
        1
    )
    print("Removed duplicate route card")
else:
    print("Duplicate block not found - inspect encoding")


path.write_text(
    text,
    encoding="utf-8"
)
from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

text = text.replace(
    "from review.render_survey import render_survey",
    "from src.review.render_survey import render_survey"
)

path.write_text(text)

print("Updated renderer import")

from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

text = text.replace(
    'onclick="focusValidationStop(${stop.stop_id})"',
    'onclick="window.location=\'/survey-page/${stop.stop_id}\'"'
)

p.write_text(text)

print("Updated validation queue click behavior")

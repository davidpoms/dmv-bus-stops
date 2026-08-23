from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

text = text.replace(
    "sii.physical_stop_id",
    "sii.stop_id"
)

path.write_text(text)

print("Fixed stop_improvement_impact join column.")
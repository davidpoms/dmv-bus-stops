from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

text = text.replace(
    "sii.priority_score",
    "io.opportunity_score"
)

text = text.replace(
    "LEFT JOIN stop_priority_snapshots sii\n                ON ps.id = sii.stop_id",
    "LEFT JOIN improvement_opportunities io\n                ON ps.id = io.physical_stop_id"
)

path.write_text(text)

print("API priority migration complete")
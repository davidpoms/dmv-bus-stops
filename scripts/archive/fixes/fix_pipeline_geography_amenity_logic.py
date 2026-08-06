from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


text = text.replace(
"""
AND (
    COALESCE(w.wmata_shelter,'') != ''
)
""",
"""
AND w.wmata_shelter = 1
"""
)


text = text.replace(
"""
AND (
    COALESCE(w.wmata_bench,'') != ''
)
""",
"""
AND w.wmata_bench = 1
"""
)


text = text.replace(
"""
AND (
    COALESCE(w.wmata_shelter,'') != ''
    OR COALESCE(w.wmata_bench,'') != ''
)
""",
"""
AND (
    w.wmata_shelter = 1
    OR w.wmata_bench = 1
)
"""
)


path.write_text(text)

print("Pipeline geography WMATA amenity logic fixed")
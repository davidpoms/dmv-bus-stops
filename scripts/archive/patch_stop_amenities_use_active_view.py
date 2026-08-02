from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """
        SELECT
            wmata_shelter,
            wmata_bench,
            wmata_accessible,
            match_confidence
        FROM stop_wmata_evidence
        WHERE physical_stop_id = ?
"""


new = """
        SELECT
            wmata_shelter,
            wmata_bench,
            wmata_accessible,
            match_confidence
        FROM active_wmata_evidence
        WHERE physical_stop_id = ?
"""


if old not in text:
    raise Exception("Amenities query not found")


text = text.replace(old, new, 1)


path.write_text(text)

print("Patched stop amenities to use active_wmata_evidence")
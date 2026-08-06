from pathlib import Path
import shutil

path = Path("src/api/app.py")

backup = path.with_suffix(".py.bak_review_fix")

shutil.copy(path, backup)

text = path.read_text()


old = '''    return jsonify(
        {
            "stop_id": row[0],
            "location": row[1],
            "lat": row[2],
            "lon": row[3],
            "heading": heading,
            "streetview_url": streetview_url,


            "wmata_evidence":
                wmata_evidence,

            "community_review":
                community_review,

            "impact_summary":
'''

new = '''    return jsonify(
        {
            "stop_id": row[0],
            "location": row[1],
            "lat": row[2],
            "lon": row[3],
            "heading": heading,
            "streetview_url": streetview_url,


            "wmata_evidence":
                wmata_evidence,

            "community_review":
                community_review,

            "impact_summary":
'''


if old not in text:
    raise SystemExit(
        "Target block not found. No changes made."
    )


text = text.replace(old, new, 1)

path.write_text(text)

print("Fixed review_stop_info mapping")
print("Backup created:", backup)
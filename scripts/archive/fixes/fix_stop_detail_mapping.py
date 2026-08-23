from pathlib import Path
import shutil

path = Path("src/api/app.py")

backup = path.with_suffix(".py.bak_stop_detail_fix")

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
'''


new = '''    return jsonify(
        {
            "stop_id": stop_id,
            "location": row[0],
            "lat": row[1],
            "lon": row[2],
            "score": row[3],
            "impact": row[4],
            "routes": row[5],
            "heading": heading,
            "streetview_url": streetview_url,
'''


if old not in text:
    raise SystemExit("Target block not found")


text = text.replace(old, new, 1)

path.write_text(text)

print("Fixed stop_detail response mapping")
print("Backup:", backup)
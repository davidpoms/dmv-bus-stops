from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''    return jsonify(
        {
            "stop":
                {
                    "location": stop[0],
                    "lat": stop[1],
                    "lon": stop[2],
                    "score": stop[3],
                    "impact": stop[4]
                }
                if stop else None,
'''

new = '''    stop_row = stop[0] if stop else None


    return jsonify(
        {
            "stop":
                {
                    "location": stop_row[0],
                    "lat": stop_row[1],
                    "lon": stop_row[2],
                    "score": stop_row[3],
                    "impact": stop_row[4]
                }
                if stop_row else None,
'''

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Fixed stop detail row handling")
else:
    print("Target block not found")

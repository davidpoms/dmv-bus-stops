from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = '''
    stop_id_requested = request.args.get(
        "stop_id"
    )
'''

new = '''
    stop_id_requested = request.args.get(
        "stop_id"
    )

    latitude = request.args.get("lat")
    longitude = request.args.get("lon")
'''

if old not in text:
    raise Exception("Could not find stop_id block")

text = text.replace(old, new)

path.write_text(text)

print("Added nearby coordinate parameters")

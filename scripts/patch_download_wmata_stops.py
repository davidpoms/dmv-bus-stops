from pathlib import Path

path = Path("scripts/download_wmata_stops.py")

if not path.exists():
    raise SystemExit("ERROR: scripts/download_wmata_stops.py not found")

text = path.read_text()

# Change batch size if present
text = text.replace(
    "batch_size = 50",
    "batch_size = 20"
)

old_start = text.find("def get_features(")

if old_start == -1:
    raise SystemExit("ERROR: Could not find get_features()")

# Find next function or main block
next_def = text.find("\ndef ", old_start + 5)

if next_def == -1:
    next_def = len(text)

new_function = r'''def get_features(ids):

    params = {
        "objectIds": ",".join(map(str, ids)),
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json"
    }

    for attempt in range(3):

        data = requests.get(
            QUERY_URL,
            params=params
        ).json()

        if "features" in data:
            return [
                f["attributes"]
                for f in data["features"]
            ]

        print(
            f"Batch failed attempt {attempt+1}/3:",
            ids[:5]
        )

        time.sleep(2)

    print("Falling back individually:", ids[:5])

    rows = []

    for oid in ids:

        data = requests.get(
            QUERY_URL,
            params={
                "objectIds": oid,
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json"
            }
        ).json()

        if "features" in data:
            rows.append(
                data["features"][0]["attributes"]
            )

        time.sleep(0.1)

    return rows

'''

text = (
    text[:old_start]
    + new_function
    + text[next_def:]
)

path.write_text(text)

print("Patched:", path)
print("Changes:")
print("- batch size reduced to 20")
print("- added batch retry logic")
print("- individual fallback only after retries")
print("- switched feature queries to outFields=*")

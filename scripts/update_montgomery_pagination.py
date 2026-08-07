from pathlib import Path


FILE = Path("scripts/import_montgomery_amenities.py")

text = FILE.read_text()


start = text.find(
    "response = requests.get("
)

end = text.find(
    "matched = 0"
)


if start == -1:
    raise Exception("Could not find requests block")

if end == -1:
    raise Exception("Could not find matched block")


replacement = """
all_features = []

offset = 0

page_size = 2000


while True:

    print(
        f"Fetching records {offset}-{offset + page_size - 1}"
    )

    params = PARAMS.copy()

    params.update(
        {
            "resultOffset": offset,
            "resultRecordCount": page_size
        }
    )


    response = requests.get(
        URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    page = data.get(
        "features",
        []
    )


    all_features.extend(page)


    if len(page) < page_size:
        break


    offset += page_size



features = all_features


print(
    "Records:",
    len(features)
)

"""


text = (
    text[:start]
    + replacement
    + text[end:]
)


FILE.write_text(text)

print("Updated Montgomery pagination")
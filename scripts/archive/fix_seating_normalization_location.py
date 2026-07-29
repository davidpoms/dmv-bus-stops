from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


start = text.find(
    '@app.route("/review/submit", methods=["POST"])'
)

if start == -1:
    raise Exception("Could not find submit route")


end = text.find(
    '    data["shelter_type"] = (',
    start
)

if end == -1:
    raise Exception("Could not find shelter_type block")


insert = """
    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )


"""


# remove any seating normalization inside this function first
function_text = text[start:end]

old = """
    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )


"""

function_text = function_text.replace(
    old,
    ""
)


# rebuild with insertion after data=request.json
marker = "    data = request.json\n"

if marker not in function_text:
    raise Exception("Could not find request.json in submit_review")


function_text = function_text.replace(
    marker,
    marker + "\n" + insert,
    1
)


text = (
    text[:start]
    + function_text
    + text[end:]
)


p.write_text(text)

print(
    "Fixed seating normalization location"
)

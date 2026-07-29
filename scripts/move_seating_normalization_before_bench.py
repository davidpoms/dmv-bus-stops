from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


block = """
    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )

"""


# remove existing copy if present
text = text.replace(block, "")


old = """    data = request.json

"""

new = """    data = request.json

""" + block


if old not in text:
    raise Exception("Could not find request.json insertion point")


text = text.replace(
    old,
    new,
    1
)


p.write_text(text)

print("Moved seating_type normalization before bench_type")

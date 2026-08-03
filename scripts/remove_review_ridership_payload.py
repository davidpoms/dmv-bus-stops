from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
            "ridership_exposure":
                ridership_exposure,

"""


if old not in text:
    raise Exception("Could not find ridership payload block")


text = text.replace(
    old,
    "",
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Removed review ridership payload")
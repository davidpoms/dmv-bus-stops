from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

insert = """
#map {
    height: 600px;
    width: 100%;
}
"""

if "#map {" not in text:
    text = text.replace(
        "</style>",
        insert + "\n</style>"
    )
    p.write_text(text)
    print("Added map CSS")
else:
    print("Map CSS already exists")

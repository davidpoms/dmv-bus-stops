from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

if "\nloadValidationQueue();\n" not in text:
    text = text.replace(
        "\nloadStops();\n",
        "\nloadStops();\nloadValidationQueue();\n"
    )
    p.write_text(text)
    print("Added validation queue call")
else:
    print("Queue call already exists")

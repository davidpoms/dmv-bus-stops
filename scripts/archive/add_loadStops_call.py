from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

if "\nloadStops();\n" not in text:
    pos = text.rfind("\n});")

    if pos != -1:
        text = (
            text[:pos]
            + "\n\nloadStops();\n"
            + text[pos:]
        )
        p.write_text(text)
        print("Inserted loadStops() call")
    else:
        print("Could not find closing wrapper")
else:
    print("loadStops already called")

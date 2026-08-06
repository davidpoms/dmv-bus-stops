from pathlib import Path

path = Path(
    "src/dashboard/static/dashboard.js"
)

lines = path.read_text().splitlines()

output = []

i = 0

while i < len(lines):

    line = lines[i]

    if "detail.impact_summary.routes.length" in line:

        indent = line[:len(line)-len(line.lstrip())]

        output.append(
            indent +
            "detail.impact_summary.routes &&"
        )

        output.append(line)

    else:
        output.append(line)

    i += 1


path.write_text(
    "\n".join(output)
)

print(
    "Added routes null guard"
)
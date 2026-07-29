from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# remove blank lines at end
while lines and lines[-1].strip() == "":
    lines.pop()

# replace final standalone } / ); ending
if lines[-2].strip() == ")" and lines[-1].strip() == ";":
    raise SystemExit("unexpected split close")

if lines[-1].strip() == "};":
    raise SystemExit("already fixed")

if lines[-1].strip() == "}" and lines[-2].strip() == ");":
    lines[-2] = "});"
    del lines[-1]
else:
    raise SystemExit(
        "Ending did not match:\n" +
        "\n".join(lines[-5:])
    )

p.write_text("\n".join(lines) + "\n")

print("fixed final DOM close")

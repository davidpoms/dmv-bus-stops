from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# Remove the second-to-last closing brace before the final DOM close
if (
    lines[-4].strip() == "}"
    and lines[-3].strip() == ");"
    and lines[-1].strip() == "});"
):
    del lines[-4]
else:
    raise SystemExit(
        "Unexpected ending:\n" +
        "\n".join(lines[-6:])
    )

p.write_text("\n".join(lines) + "\n")

print("removed extra closing brace")

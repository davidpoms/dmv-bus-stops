from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# remove final malformed section after location.reload()
while lines and lines[-1].strip() != "location.reload();":
    lines.pop()

# append correct closures
lines.extend([
    "",
    "                }",
    "            );",
    "",
    "        }",
    "",
    "    }",
    "",
    ");",
    "",
    "});"
])

p.write_text("\n".join(lines) + "\n")

print("rebuilt final click listener closure")

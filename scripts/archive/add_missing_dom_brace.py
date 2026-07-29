from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# remove trailing whitespace-only lines
while lines and not lines[-1].strip():
    lines.pop()

# Current ending:
#     }
# );
#
# Need:
#     }
# }
# );

if (
    len(lines) >= 3
    and lines[-1].strip() == ");"
    and lines[-2].strip() == "}"
    and lines[-3].strip() == "}"
):
    lines.insert(len(lines)-1, "}")
else:
    raise SystemExit(
        "Unexpected ending:\n" +
        "\n".join(lines[-8:])
    )

p.write_text("\n".join(lines) + "\n")

print("added missing DOMContentLoaded brace")

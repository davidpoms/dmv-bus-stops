from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# remove the stray:
#
#     }
#
# );
#
# immediately before final });
if (
    lines[-4].strip() == "}"
    and lines[-3].strip() == ");"
    and lines[-1].strip() == "});"
):
    del lines[-4:-2]
else:
    raise SystemExit(
        "Ending not matched:\n" +
        "\n".join(lines[-8:])
    )

p.write_text("\n".join(lines) + "\n")

print("removed extra click listener close")

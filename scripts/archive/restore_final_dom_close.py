from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

while lines and not lines[-1].strip():
    lines.pop()

print("Current ending:")
print("\n".join(lines[-8:]))

# Current ending should be:
#         }
#     );
#
# Add the DOMContentLoaded close.

if (
    lines[-1].strip() == ");"
    and lines[-2].strip() == "}"
):
    lines.append("")
    lines.append("});")
else:
    raise SystemExit("Unexpected ending, not safe to patch")

p.write_text("\n".join(lines) + "\n")

print("restored DOM close")

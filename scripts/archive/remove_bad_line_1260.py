from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# remove the extra standalone brace immediately before the final );
for i in range(len(lines)-3, len(lines)):
    print(i+1, repr(lines[i]))

# expected:
# line before final ); is "    }"
# the extra one is the line before that

if (
    lines[-3].strip() == "}"
    and lines[-2].strip() == ");"
    and lines[-1].strip() == "});"
):
    del lines[-3]
else:
    raise SystemExit("Ending did not match expected pattern")

p.write_text("\n".join(lines) + "\n")

print("removed extra closing brace")

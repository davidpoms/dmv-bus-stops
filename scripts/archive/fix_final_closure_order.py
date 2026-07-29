from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

while lines and not lines[-1].strip():
    lines.pop()

print("Current ending:")
print("\n".join(lines[-10:]))

# Replace the final malformed:
#
#     }
# }
# );
#
# with:
#
#         }
#     );
# }
# );

if lines[-3].strip() == "}" and lines[-2].strip() == "}" and lines[-1].strip() == ");":
    lines[-3:] = [
        "        }",
        "    );",
        "}"
        ");"
    ]
else:
    raise SystemExit("Unexpected ending")

p.write_text("\n".join(lines) + "\n")

print("fixed closure order")

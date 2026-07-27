from pathlib import Path

path = Path("src/database/schema.sql")

text = path.read_text()

if "concrete_pad_needed TEXT" in text:
    print("Schema already updated. No changes made.")
    raise SystemExit(0)

old = """
    bench_feasible TEXT,

    ada_clearance_possible TEXT,
"""

new = """
    bench_feasible TEXT,

    concrete_pad_needed TEXT,

    ada_clearance_possible TEXT,
"""

if old not in text:
    raise SystemExit(
        "Could not find expected schema section."
    )

text = text.replace(
    old,
    new,
    1
)

path.write_text(text)

print(
    "Updated schema.sql with concrete_pad_needed field."
)

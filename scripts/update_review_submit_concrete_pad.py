from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

if "data.get(\"concrete_pad_needed\")" in text:
    print("review submit already updated.")
    raise SystemExit(0)

old_fields = """
            steward_email,
            steward_candidate
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

new_fields = """
            steward_email,
            steward_candidate,
            concrete_pad_needed
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

if old_fields not in text:
    raise SystemExit(
        "Could not find expected INSERT field section."
    )

text = text.replace(
    old_fields,
    new_fields,
    1
)


old_values = """
            data.get("steward_email"),
            data.get("steward_candidate", 0)
        )
"""

new_values = """
            data.get("steward_email"),
            data.get("steward_candidate", 0),
            data.get("concrete_pad_needed")
        )
"""

if old_values not in text:
    raise SystemExit(
        "Could not find expected INSERT values section."
    )

text = text.replace(
    old_values,
    new_values,
    1
)

path.write_text(text)

print(
    "Updated /review/submit with concrete_pad_needed field"
)

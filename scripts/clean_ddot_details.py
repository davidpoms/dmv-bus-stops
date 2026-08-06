from pathlib import Path


path = Path("src/assessment/interpretation.py")

text = path.read_text()


old = '''                "details":
                    record.get("notes")
'''


new = '''                "details":
                    (
                        record.get("notes")
                        .replace(
                            "DDOT procurement shelter inventory.",
                            "DDOT asset record."
                        )
                        if record.get("notes")
                        else None
                    )
'''


if old not in text:
    raise Exception(
        "Could not find DDOT details block"
    )


path.write_text(
    text.replace(old,new)
)

print(
    "Cleaned DDOT evidence details"
)
from pathlib import Path

path = Path("src/assessment/interpretation.py")

text = path.read_text(encoding="utf-8")

text = text.replace(
'''                "details":
                    (
                        record.get("notes")
                        .replace(
                            "DDOT procurement shelter inventory.",
                            "DDOT asset record."
                        )
                        if record.get("notes")
                        else None
                    )''',
'''                "details":
                    (
                        "Matched DDOT asset record."
                        if evidence_class == "current_asset"
                        else None
                    )'''
)

path.write_text(
    text,
    encoding="utf-8"
)

print("Cleaned DDOT interpretation details")
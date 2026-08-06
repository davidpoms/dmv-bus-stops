from pathlib import Path


path = Path("src/assessment/interpretation.py")

text = path.read_text()


old = '''        results.append(
            {
                "source":
                    "DDOT shelter inventory",

                "source_record":
                    record.get("ddot_id"),
'''


new = '''        source_label = (
            "DDOT API shelter asset record"
            if record.get("api_id")
            else
            "DDOT shelter procurement inventory July 2026"
        )


        results.append(
            {
                "source":
                    source_label,

                "source_type":
                    (
                        "api"
                        if record.get("api_id")
                        else
                        "procurement"
                    ),

                "source_record":
                    record.get("ddot_id")
                    or record.get("api_id"),
'''


if old not in text:
    raise Exception(
        "Could not find DDOT source block"
    )


text = text.replace(
    old,
    new
)


path.write_text(text)

print(
    "Updated DDOT provenance labeling"
)
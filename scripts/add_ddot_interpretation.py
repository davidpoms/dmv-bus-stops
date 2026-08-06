from pathlib import Path


path = Path("src/assessment/interpretation.py")

text = path.read_text(encoding="utf-8")


addition = """



def interpret_ddot_evidence(ddot_records):

    results = []

    for record in ddot_records or []:

        status = record.get(
            "lifecycle_status"
        )

        if status == "CONFIRMED_ACTIVE":
            finding = (
                "DDOT records indicate an active "
                "shelter installation at this stop."
            )

        elif status == "REMOVED_BUT_ROUTE_ACTIVE":
            finding = (
                "DDOT previously recorded shelter "
                "infrastructure, but the lifecycle "
                "status indicates it may no longer exist."
            )

        elif status == "POSSIBLE_NEW_DDOT_SHELTER":
            finding = (
                "DDOT records suggest a possible "
                "new shelter location requiring validation."
            )

        else:
            finding = (
                "DDOT shelter inventory record available "
                "for this stop."
            )


        results.append(
            {
                "source":
                    "DDOT shelter inventory",

                "source_record":
                    record.get("ddot_id"),

                "finding":
                    finding,

                "routes":
                    record.get("routes", []),

                "confidence":
                    record.get("confidence"),

                "details":
                    record.get("notes")
            }
        )


    return results
"""


if "def interpret_ddot_evidence" not in text:

    text += addition

    path.write_text(
        text,
        encoding="utf-8"
    )


print(
    "Added DDOT evidence interpretation"
)
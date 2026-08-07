from pathlib import Path


path = Path("src/assessment/interpretation.py")

text = path.read_text(encoding="utf-8")


start = text.find("def interpret_ddot_evidence")

if start == -1:
    raise SystemExit(
        "Could not find interpret_ddot_evidence function"
    )


# Find the end of the function.
# This function is currently at the end of the file,
# so replace through EOF.
old = text[start:]


new = r'''
def interpret_ddot_evidence(ddot_records):

    results = []

    for record in ddot_records or []:

        status = record.get(
            "lifecycle_status"
        )

        has_inventory_match = (
            status == "CONFIRMED_ACTIVE"
            and record.get("ddot_id")
            and str(record.get("ddot_id")).lower() != "nan"
        )

        has_api_only = (
            status == "API_ONLY_ACTIVE_STOP"
            or (
                record.get("api_id")
                and not has_inventory_match
            )
        )


        if has_inventory_match:

            evidence_class = "current_asset"

            public_status = (
                "Verified DDOT shelter asset"
            )

            finding = (
                "DDOT shelter inventory records "
                "identify a shelter asset associated "
                "with this stop."
            )


        elif status == "POSSIBLE_NEW_DDOT_SHELTER":

            evidence_class = "possible_asset"

            public_status = (
                "DDOT shelter record requires validation"
            )

            finding = (
                "DDOT records suggest a possible "
                "new shelter location requiring "
                "additional validation."
            )


        elif status == "REMOVED_BUT_ROUTE_ACTIVE":

            evidence_class = "historical_asset"

            public_status = (
                "Historical DDOT shelter record"
            )

            finding = (
                "DDOT records previously associated "
                "shelter infrastructure with this "
                "location, but current installation "
                "status is uncertain."
            )


        elif has_api_only:

            evidence_class = "api_only"

            public_status = (
                "DDOT asset record requires validation"
            )

            finding = (
                "DDOT asset records identify shelter "
                "infrastructure associated with this "
                "location, but a current inventory "
                "match was not found."
            )


        else:

            evidence_class = "unverified"

            public_status = (
                "DDOT record requires validation"
            )

            finding = (
                "DDOT shelter-related evidence exists "
                "for this location, but installation "
                "status could not be confirmed."
            )


        source_label = (
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

                "lifecycle_status":
                    status,

                "evidence_class":
                    evidence_class,

                "public_status":
                    public_status,

                "finding":
                    finding,

                "routes":
                    record.get("routes", []),

                "confidence":
                    record.get("confidence"),

                "details":
                    (
                        record.get("notes")
                        .replace(
                            "DDOT procurement shelter inventory.",
                            "DDOT asset record."
                        )
                        if record.get("notes")
                        else None
                    )
            }
        )


    return results
'''


path.write_text(
    text[:start] + new,
    encoding="utf-8"
)


print(
    "Updated DDOT interpretation logic"
)
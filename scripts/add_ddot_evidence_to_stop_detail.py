from pathlib import Path


def replace_once(path, old, new):
    text = Path(path).read_text(encoding="utf-8")

    if new in text:
        print(f"Already patched: {path}")
        return

    if old not in text:
        raise Exception(f"Could not find target in {path}")

    text = text.replace(old, new, 1)

    Path(path).write_text(text, encoding="utf-8")

    print(f"Patched: {path}")


def main():

    # -----------------------
    # app.py
    # -----------------------

    app = "src/api/app.py"

    replace_once(
        app,

        """    reviews = conn.execute(
        \"\"\"
        SELECT *
        FROM stop_observations
        WHERE physical_stop_id=?
        ORDER BY observed_at DESC
        \"\"\",
        (stop_id,)
    ).fetchall()
""",

        """    ddot = conn.execute(
        \"\"\"
        SELECT *
        FROM stop_ddot_shelter_evidence
        WHERE physical_stop_id=?
        ORDER BY created_at DESC
        \"\"\",
        (stop_id,)
    ).fetchall()


    reviews = conn.execute(
        \"\"\"
        SELECT *
        FROM stop_observations
        WHERE physical_stop_id=?
        ORDER BY observed_at DESC
        \"\"\",
        (stop_id,)
    ).fetchall()
"""
    )


    replace_once(
        app,

        """        "osm": dict(osm) if osm else None,

        "reviews": [
            dict(r)
            for r in reviews
        ]
""",

        """        "osm": dict(osm) if osm else None,

        "ddot": [
            dict(r)
            for r in ddot
        ],

        "reviews": [
            dict(r)
            for r in reviews
        ]
"""
    )


    # -----------------------
    # interpretation.py
    # -----------------------

    interp = "src/assessment/interpretation.py"


    replace_once(
        interp,

        """    osm = evidence.get("osm") or {}
    transit = evidence.get("transit") or {}
    reviews = evidence.get("reviews") or []
""",

        """    osm = evidence.get("osm") or {}
    transit = evidence.get("transit") or {}
    ddot = evidence.get("ddot") or []
    reviews = evidence.get("reviews") or []
"""
    )


    replace_once(
        interp,

        """        "community_reviews":
            len(reviews),

        "data_sources": [
""",

        """        "community_reviews":
            len(reviews),


        "ddot_shelter": {

            "records":
                len(ddot),

            "confirmed_active":
                any(
                    r.get("lifecycle_status")
                    == "CONFIRMED_ACTIVE"
                    for r in ddot
                ),

            "possible_new":
                any(
                    r.get("lifecycle_status")
                    == "POSSIBLE_NEW_DDOT_SHELTER"
                    for r in ddot
                ),

            "removed":
                any(
                    r.get("lifecycle_status")
                    == "MATCHED_REMOVED"
                    for r in ddot
                ),

            "routes":
                sorted(
                    {
                        route
                        for r in ddot
                        for route in
                        (r.get("route_ids") or "").split(",")
                        if route
                    }
                )
        },


        "data_sources": [
"""
    )


    print()
    print("DDOT evidence API patch complete")


if __name__ == "__main__":
    main()
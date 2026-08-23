from pathlib import Path


FILE = Path(
    "src/assessment/score_improvement_opportunities.py"
)


def main():

    text = FILE.read_text(
        encoding="utf-8"
    )

    backup = FILE.with_suffix(
        ".py.backup"
    )

    backup.write_text(
        text,
        encoding="utf-8"
    )


    old = """
        SELECT

            oa.physical_stop_id,

            oa.combined_route_weekday_boardings,

            oa.highest_route_weekday_boardings,

            oa.routes_served,

            oa.wmata_stop_records,
    """


    new = """
        SELECT

            oa.physical_stop_id,

            COALESCE(
                sps.factors,
                '{}'
            ),

            oa.combined_route_weekday_boardings,

            oa.highest_route_weekday_boardings,

            oa.routes_served,

            oa.wmata_stop_records,
    """


    if old not in text:
        raise Exception(
            "Could not find SELECT block"
        )


    text = text.replace(
        old,
        new
    )


    old = """
        FROM opportunity_assessments oa
    """


    new = """
        FROM opportunity_assessments oa

        LEFT JOIN stop_priority_snapshots sps

            ON sps.stop_id = oa.physical_stop_id
    """


    if old not in text:
        raise Exception(
            "Could not find FROM block"
        )


    text = text.replace(
        old,
        new,
        1
    )


    old = """
        (
            physical_stop_id,

            total_daily,

            highest_route,

            routes,

            records,
    """


    new = """
        (
            physical_stop_id,

            priority_factors,

            total_daily,

            highest_route,

            routes,

            records,
    """


    if old not in text:
        raise Exception(
            "Could not find unpack block"
        )


    text = text.replace(
        old,
        new
    )


    old = """
        route_exposure_score = normalize(
            total_daily,
            max_daily
        )
    """


    new = """
        route_exposure_score = 0

        if priority_factors:

            factors = json.loads(
                priority_factors
            )

            route_exposure_score = (
                factors.get(
                    "route_exposure_score",
                    0
                )
            )
    """


    if old not in text:
        raise Exception(
            "Could not find score block"
        )


    text = text.replace(
        old,
        new
    )


    FILE.write_text(
        text,
        encoding="utf-8"
    )


    print(
        "Patch complete"
    )

    print(
        f"Backup: {backup}"
    )


if __name__ == "__main__":
    main()
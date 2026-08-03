from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = '''"community_impact": {

    "daily_route_exposure":
        impact[0][0]
        if impact
        else None
    }
'''


new = '''"community_impact": {

    "daily_route_exposure":
        impact[0][0]
        if impact
        else None,

    "routes":
        (
            query_db(
                """
                SELECT
                    GROUP_CONCAT(DISTINCT r.route_id)

                FROM physical_stop_members psm

                JOIN stop_routes sr
                    ON psm.bus_stop_id = sr.stop_id

                JOIN routes r
                    ON sr.route_id = r.route_id

                WHERE psm.physical_stop_id=?

                """,
                (stop_id,)
            )[0][0].split(",")
            if query_db(
                """
                SELECT
                    GROUP_CONCAT(DISTINCT r.route_id)

                FROM physical_stop_members psm

                JOIN stop_routes sr
                    ON psm.bus_stop_id = sr.stop_id

                JOIN routes r
                    ON sr.route_id = r.route_id

                WHERE psm.physical_stop_id=?

                """,
                (stop_id,)
            )[0][0]
            else []
        )
    }
'''


if old not in text:
    raise Exception(
        "Target community impact block not found"
    )


text = text.replace(old, new)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Added routes to completion impact"
)
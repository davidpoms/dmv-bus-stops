import sqlite3


DB = "src/database/dmv_bus_stops.db"


def main():

    conn = sqlite3.connect(DB)
    c = conn.cursor()


    print("\nTransit integrity audit")
    print("======================\n")


    # Montgomery County should only have M routes
    montgomery = c.execute("""
        SELECT
            bs.external_stop_id,
            bs.stop_name,
            r.route_id
        FROM bus_stops bs
        JOIN stop_jurisdiction sj
            ON sj.stop_id = bs.id
        JOIN stop_routes sr
            ON sr.stop_id = bs.id
        JOIN routes r
            ON r.route_id = sr.route_id
        WHERE sj.county = 'Montgomery'
          AND r.route_id NOT LIKE 'M%'
          AND r.route_id NOT LIKE 'P%'
        ORDER BY r.route_id
    """).fetchall()


    print(
        "Montgomery County invalid routes:",
        len(montgomery)
    )

    for row in montgomery[:20]:
        print(row)



    # Prince George's should primarily have P routes
    pg = c.execute("""
        SELECT
            bs.external_stop_id,
            bs.stop_name,
            r.route_id
        FROM bus_stops bs
        JOIN stop_jurisdiction sj
            ON sj.stop_id = bs.id
        JOIN stop_routes sr
            ON sr.stop_id = bs.id
        JOIN routes r
            ON r.route_id = sr.route_id
        WHERE sj.county LIKE '%Prince George%'
          AND r.route_id NOT LIKE 'P%'
        ORDER BY r.route_id
    """).fetchall()


    print(
        "\nPrince George's unexpected routes:",
        len(pg)
    )

    for row in pg[:20]:
        print(row)



    # Find DC-style routes accidentally appearing in MD
    md_dc_routes = c.execute("""
        SELECT
            sj.county,
            r.route_id,
            COUNT(*)
        FROM stop_jurisdiction sj
        JOIN bus_stops bs
            ON bs.id = sj.stop_id
        JOIN stop_routes sr
            ON sr.stop_id = bs.id
        JOIN routes r
            ON r.route_id = sr.route_id
        WHERE sj.county IN (
            'Montgomery',
            'Prince George''s'
        )
        AND r.route_id NOT LIKE 'M%'
        AND r.route_id NOT LIKE 'P%'
        GROUP BY
            sj.county,
            r.route_id
        ORDER BY
            sj.county,
            r.route_id
    """).fetchall()


    print(
        "\nMaryland non-M/P routes:"
    )

    if md_dc_routes:
        for row in md_dc_routes:
            print(row)
    else:
        print("None")


    print(
        "\nAudit complete."
    )

    conn.close()


if __name__ == "__main__":
    main()
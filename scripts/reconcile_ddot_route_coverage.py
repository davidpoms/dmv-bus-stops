import sqlite3
import pandas as pd


DB = "src/database/dmv_bus_stops.db"
CSV = "ddot_lifecycle_reconciliation.csv"


def main():

    print("Loading reconciliation...")
    df = pd.read_csv(CSV)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row


    results = []


    for _, row in df.iterrows():

        status = row["status"]

        if status not in [
            "SPREADSHEET_ONLY",
            "API_ONLY",
            "ID_CHANGED",
            "MATCHED_ACTIVE",
            "MATCHED_REMOVED"
        ]:
            continue


        address = row["address"]


        # Find nearest physical stop by address text first
        # fallback is coordinate-based not available in CSV currently

        matches = conn.execute(
            """
            SELECT
                ps.id AS physical_stop_id,
                ps.primary_name
            FROM physical_stops ps
            WHERE ps.primary_name LIKE ?
            LIMIT 5
            """,
            (
                f"%{str(address).split(',')[0]}%",
            )
        ).fetchall()


        for m in matches:

            routes = conn.execute(
                """
                SELECT
                    r.route_id,
                    r.route_name
                FROM physical_stop_members psm

                JOIN bus_stops b
                ON b.id = psm.bus_stop_id

                JOIN stop_routes sr
                ON sr.stop_id = b.id

                JOIN routes r
                ON r.id = sr.route_id

                WHERE psm.physical_stop_id=?

                GROUP BY r.route_id
                """,
                (
                    m["physical_stop_id"],
                )
            ).fetchall()


            results.append({

                "status": status,
                "ddot_id": row.get("api_id")
                    if pd.notna(row.get("api_id"))
                    else row.get("spreadsheet_id"),

                "address": address,

                "physical_stop_id":
                    m["physical_stop_id"],

                "primary_name":
                    m["primary_name"],

                "route_count":
                    len(routes),

                "routes":
                    ",".join(
                        [
                            x["route_id"]
                            for x in routes
                        ]
                    )

            })


    out = pd.DataFrame(results)


    out.to_csv(
        "ddot_route_coverage.csv",
        index=False
    )


    print()
    print(
        "Records with physical matches:",
        len(out)
    )

    print()

    print(
        out.groupby(
            [
                "status",
                "route_count"
            ]
        ).size()
    )


    print(
        "\nWritten ddot_route_coverage.csv"
    )


if __name__ == "__main__":
    main()
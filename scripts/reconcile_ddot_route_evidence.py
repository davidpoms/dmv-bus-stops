import sqlite3
import pandas as pd


DB = "src/database/dmv_bus_stops.db"

LIFECYCLE = "ddot_lifecycle_reconciliation.csv"
OUTPUT = "ddot_route_evidence_reconciliation.csv"


def find_bus_stop_matches(conn, ddot_id):

    if pd.isna(ddot_id):
        return []

    ddot_id = str(ddot_id).replace(".0", "").strip()

    rows = conn.execute(
        """
        SELECT
            b.id,
            b.external_stop_id
        FROM bus_stops b
        WHERE
            b.external_stop_id = ?
            OR
            SUBSTR(b.external_stop_id,2)=?
        """,
        (
            ddot_id,
            ddot_id[1:] if len(ddot_id) > 1 else ddot_id
        )
    ).fetchall()

    return rows



def get_physical_routes(conn, bus_stop_ids):

    if not bus_stop_ids:
        return None

    placeholders = ",".join(["?"] * len(bus_stop_ids))

    row = conn.execute(
        f"""
        SELECT
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes,
            GROUP_CONCAT(DISTINCT ps.id) AS physical_stop_ids

        FROM physical_stop_members psm

        JOIN physical_stops ps
            ON ps.id = psm.physical_stop_id

        LEFT JOIN stop_routes sr
            ON sr.stop_id = psm.bus_stop_id

        LEFT JOIN routes r
            ON r.id = sr.route_id

        WHERE psm.bus_stop_id IN ({placeholders})
        """,
        bus_stop_ids
    ).fetchone()

    return dict(row)



def main():

    print("Loading lifecycle reconciliation...")
    df = pd.read_csv(LIFECYCLE)

    print("Rows:", len(df))


    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row


    results = []


    for _, row in df.iterrows():

        ddot_ids = []

        for col in ["spreadsheet_id", "api_id"]:

            value = row[col]

            if pd.notna(value):
                ddot_ids.append(
                    str(value)
                    .replace(".0","")
                    .strip()
                )


        bus_ids = []

        for ddot_id in ddot_ids:

            matches = find_bus_stop_matches(
                conn,
                ddot_id
            )

            for m in matches:
                bus_ids.append(m["id"])


        bus_ids = list(set(bus_ids))


        route_info = get_physical_routes(
            conn,
            bus_ids
        )


        if route_info is None:
            route_info = {
                "route_count":0,
                "routes":None,
                "physical_stop_ids":None
            }


        result = dict(row)

        result.update(route_info)


        result["has_gtfs_route"] = (
            result["route_count"] or 0
        ) > 0


        results.append(result)


    conn.close()


    out = pd.DataFrame(results)


    def classify(row):

        if (
            row["status"]=="SPREADSHEET_ONLY"
            and row["has_gtfs_route"]
        ):
            return "POSSIBLE_NEW_DDOT_SHELTER"

        if (
            row["status"]=="API_ONLY"
            and row["has_gtfs_route"]
        ):
            return "API_ONLY_ACTIVE_STOP"

        if (
            row["status"]=="MATCHED_ACTIVE"
            and row["has_gtfs_route"]
        ):
            return "CONFIRMED_ACTIVE"

        if (
            row["status"]=="MATCHED_REMOVED"
            and row["has_gtfs_route"]
        ):
            return "REMOVED_BUT_ROUTE_ACTIVE"

        if row["has_gtfs_route"]:
            return "ROUTE_PRESENT"

        return "NO_ROUTE"


    out["route_evidence_status"] = out.apply(
        classify,
        axis=1
    )


    print()
    print(
        out["route_evidence_status"]
        .value_counts()
    )


    print("\nPossible new shelters:")
    print(
        out[
            out.route_evidence_status ==
            "POSSIBLE_NEW_DDOT_SHELTER"
        ][
            [
                "spreadsheet_id",
                "api_id",
                "address",
                "routes",
                "physical_stop_ids"
            ]
        ]
        .head(50)
        .to_string(index=False)
    )


    out.to_csv(
        OUTPUT,
        index=False
    )

    print()
    print("Written:", OUTPUT)



if __name__ == "__main__":
    main()
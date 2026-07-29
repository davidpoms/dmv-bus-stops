import sqlite3
import pandas as pd


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)


query = """
WITH stop_route_detail AS (

    SELECT
        psm.physical_stop_id,
        sr.route_id,
        r.route_name,

        rs.weekday_boardings,
        rs.monthly_boardings

    FROM stop_routes sr

    JOIN bus_stops bs
        ON sr.stop_id = bs.id

    JOIN physical_stop_members psm
        ON bs.id = psm.bus_stop_id

    JOIN routes r
        ON sr.route_id = r.route_id

    LEFT JOIN ridership_snapshots rs
        ON sr.route_id = rs.route_id

)

SELECT
    physical_stop_id,

    COUNT(DISTINCT route_id)
        AS route_count,

    GROUP_CONCAT(
        DISTINCT route_id
    )
        AS routes_serving,

    SUM(
        COALESCE(weekday_boardings,0)
    )
        AS weekday_route_boarding_exposure,

    SUM(
        COALESCE(monthly_boardings,0)
    )
        AS monthly_route_boarding_exposure,

    MAX(
        COALESCE(weekday_boardings,0)
    )
        AS highest_route_weekday_boardings

FROM stop_route_detail

GROUP BY physical_stop_id

"""


df = pd.read_sql(
    query,
    conn
)


print("Stops with route exposure:")
print(len(df))

print()

print(df.head().to_string())


df.to_csv(
    "data/stop_transit_exposure.csv",
    index=False
)


print()
print(
    "Saved data/stop_transit_exposure.csv"
)

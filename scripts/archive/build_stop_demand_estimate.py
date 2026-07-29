import sqlite3
import pandas as pd


DB = "src/database/dmv_bus_stops.db"

OUTPUT = "data/stop_demand_estimate.csv"


conn = sqlite3.connect(DB)


print("Loading route ridership...")

ridership = pd.read_sql(
    """
    SELECT
        route_id,
        weekday_boardings,
        monthly_boardings
    FROM ridership_snapshots
    WHERE service_type = 'Metrobus'
    """,
    conn
)


print("Loading stop routes...")

stop_routes = pd.read_sql(
    """
    SELECT
        stop_id,
        route_id
    FROM stop_routes
    """,
    conn
)


print("Loading physical stops...")

stops = pd.read_sql(
    """
    SELECT
        id AS physical_stop_id,
        primary_name,
        latitude,
        longitude
    FROM physical_stops
    """,
    conn
)


print("Routes:", len(ridership))
print("Stop-route pairs:", len(stop_routes))
print("Physical stops:", len(stops))


#
# Count how many stops each route serves
#

route_stop_counts = (
    stop_routes
    .groupby("route_id")
    ["stop_id"]
    .nunique()
    .reset_index()
    .rename(
        columns={
            "stop_id": "route_stop_count"
        }
    )
)


#
# Attach route ridership
#

route_demand = ridership.merge(
    route_stop_counts,
    on="route_id",
    how="inner"
)


#
# Allocate route ridership evenly
#

route_demand["weekday_boardings_per_stop"] = (
    route_demand["weekday_boardings"]
    /
    route_demand["route_stop_count"]
)


route_demand["monthly_boardings_per_stop"] = (
    route_demand["monthly_boardings"]
    /
    route_demand["route_stop_count"]
)


#
# Attach demand to stop-route pairs
#

stop_demand = stop_routes.merge(
    route_demand[
        [
            "route_id",
            "weekday_boardings_per_stop",
            "monthly_boardings_per_stop"
        ]
    ],
    on="route_id",
    how="inner"
)


#
# Aggregate routes serving each physical stop
#

stop_summary = (
    stop_demand
    .groupby("stop_id")
    .agg(
        route_count=("route_id", "nunique"),
        routes_serving=("route_id",
                        lambda x: ",".join(sorted(set(x)))),
        estimated_weekday_boardings=(
            "weekday_boardings_per_stop",
            "sum"
        ),
        estimated_monthly_boardings=(
            "monthly_boardings_per_stop",
            "sum"
        )
    )
    .reset_index()
)


stop_summary = stop_summary.rename(
    columns={
        "stop_id": "physical_stop_id"
    }
)


#
# Join names/location
#

result = stops.merge(
    stop_summary,
    on="physical_stop_id",
    how="inner"
)


result["demand_confidence"] = "LOW"


result = result.sort_values(
    "estimated_weekday_boardings",
    ascending=False
)


result.to_csv(
    OUTPUT,
    index=False
)


print()
print("Saved:", OUTPUT)
print("Stops scored:", len(result))


print()
print(
    result.head(20).to_string(index=False)
)

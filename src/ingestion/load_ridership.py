"""
DMV Bus Stops Intelligence Platform

WMATA Metrobus ridership ingestion.

Purpose:
- Load route-level ridership data
- Normalize service categories
- Create demand metrics
- Prepare route demand data for joining
  to bus stops

Important:
This dataset represents route demand,
not individual stop boardings.

Stop-level demand will be estimated later.
"""


from pathlib import Path

import csv

from src.config import RIDERSHIP_FILE



# ------------------------------------------------------------
# Field detection
#
# WMATA exports may change column names.
# ------------------------------------------------------------

ROUTE_FIELDS = [
    "Route",
    "ROUTE",
    "route"
]


SERVICE_FIELDS = [
    "Service Type",
    "SERVICE_TYPE",
    "service_type"
]


BOARDING_FIELDS = [
    "Monthly Boardings",
    "MONTHLY_BOARDINGS",
    "boardings"
]




def find_column(fieldnames, candidates):

    """
    Find first matching column.
    """

    for field in candidates:

        if field in fieldnames:

            return field


    return None





def load_ridership(filepath=RIDERSHIP_FILE):

    """
    Load WMATA route ridership CSV.

    Returns:

    [
        {
            route_id,
            service_type,
            monthly_boardings
        }
    ]

    """

    filepath = Path(filepath)


    if not filepath.exists():

        raise FileNotFoundError(
            f"Ridership file not found: {filepath}"
        )



    records = []



    with open(
        filepath,
        "r",
        encoding="utf-8"
    ) as f:


        reader = csv.DictReader(f)



        route_field = find_column(
            reader.fieldnames,
            ROUTE_FIELDS
        )


        service_field = find_column(
            reader.fieldnames,
            SERVICE_FIELDS
        )


        boarding_field = find_column(
            reader.fieldnames,
            BOARDING_FIELDS
        )



        if not route_field:

            raise ValueError(
                "Could not find route column"
            )


        if not boarding_field:

            raise ValueError(
                "Could not find ridership column"
            )



        for row in reader:


            route = row.get(route_field)


            if not route:

                continue



            try:

                boardings = float(
                    row.get(boarding_field, 0)
                )

            except ValueError:

                boardings = 0



            records.append(

                {

                    "route_id": route.strip(),

                    "service_type": (
                        row.get(service_field)
                        if service_field
                        else None
                    ),

                    "monthly_boardings": boardings

                }

            )



    return records





def summarize_ridership(records):

    """
    Print basic ridership diagnostics.
    """

    print(
        f"Loaded {len(records)} ridership records"
    )


    total = sum(
        r["monthly_boardings"]
        for r in records
    )


    print(
        f"Total reported monthly boardings: {total:,.0f}"
    )



    routes = set(
        r["route_id"]
        for r in records
    )


    print(
        f"Routes represented: {len(routes)}"
    )





def calculate_route_demand(records):

    """
    Collapse multiple service categories into
    one route demand score.

    Example:

    Route C53:
        weekday
        saturday
        sunday

    becomes:

    {
        C53: total_demand
    }

    """

    demand = {}


    for record in records:


        route = record["route_id"]


        demand.setdefault(
            route,
            0
        )


        demand[route] += (
            record["monthly_boardings"]
        )



    return demand





if __name__ == "__main__":


    records = load_ridership()


    summarize_ridership(records)


    demand = calculate_route_demand(records)


    print(
        "Example routes:"
    )


    for route, value in list(demand.items())[:10]:

        print(
            route,
            f"{value:,.0f}"
        )

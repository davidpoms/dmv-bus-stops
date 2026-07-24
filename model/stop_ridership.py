"""
Build stop-level ridership intelligence
from database relationships.
"""



def build_stop_ridership(stop_id, route_records):
    """
    Convert route ridership records
    into stop demand input.

    route_records example:

    [
        {
            "route_id": "C53",
            "monthly_boardings": 389211
        }
    ]
    """


    if not route_records:

        return {
            "stop_id": stop_id,
            "routes": [],
            "total_boardings": 0,
            "demand_score": 0
        }


    total_boardings = sum(
        r["monthly_boardings"]
        for r in route_records
    )


    route_count = len(route_records)


    if total_boardings >= 500000:
        demand_score = 100

    elif total_boardings >= 250000:
        demand_score = 85

    elif total_boardings >= 100000:
        demand_score = 70

    elif total_boardings >= 50000:
        demand_score = 50

    else:
        demand_score = 25


    return {

        "stop_id": stop_id,

        "routes": [
            r["route_id"]
            for r in route_records
        ],

        "route_count": route_count,

        "total_boardings": total_boardings,

        "demand_score": demand_score

    }

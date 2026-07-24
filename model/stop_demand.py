"""
Stop-level demand intelligence.

Combines route ridership into a demand
estimate for individual bus stops.
"""


def calculate_stop_demand(routes):
    """
    Calculate demand score for a stop.

    routes should be a list of dictionaries:

    [
        {
            "route_id": "C53",
            "monthly_boardings": 389211
        }
    ]

    """

    if not routes:
        return {
            "route_count": 0,
            "total_boardings": 0,
            "demand_score": 0
        }


    total_boardings = sum(
        route["monthly_boardings"]
        for route in routes
    )


    highest_route = max(
        routes,
        key=lambda route: route["monthly_boardings"]
    )


    # Normalize to a 0-100 score
    if total_boardings >= 500000:
        score = 100

    elif total_boardings >= 250000:
        score = 85

    elif total_boardings >= 100000:
        score = 70

    elif total_boardings >= 50000:
        score = 50

    else:
        score = 25


    return {
        "route_count": len(routes),
        "total_boardings": total_boardings,
        "highest_demand_route": highest_route["route_id"],
        "demand_score": score
    }

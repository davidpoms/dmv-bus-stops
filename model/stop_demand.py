"""
Stop-level demand intelligence.

Combines route-level daily ridership
into an estimated stop demand score.
"""


def calculate_stop_demand(routes):
    """
    Calculate stop demand from routes.

    Example input:

    [
        {
            "route_id": "C53",
            "average_daily_boardings": 12974
        },
        {
            "route_id": "D40",
            "average_daily_boardings": 10226
        }
    ]
    """

    if not routes:

        return {
            "route_count": 0,
            "estimated_daily_demand": 0,
            "demand_score": 0,
            "confidence": "low"
        }


    total_daily_boardings = sum(
        route["average_daily_boardings"]
        for route in routes
    )


    route_count = len(routes)


    if total_daily_boardings >= 20000:
        score = 100
        level = "very_high"

    elif total_daily_boardings >= 10000:
        score = 85
        level = "high"

    elif total_daily_boardings >= 5000:
        score = 65
        level = "medium"

    else:
        score = 35
        level = "low"


    if route_count >= 3:
        confidence = "high"

    elif route_count == 2:
        confidence = "medium"

    else:
        confidence = "low"


    return {

        "route_count": route_count,

        "estimated_daily_demand":
            total_daily_boardings,

        "demand_level":
            level,

        "demand_score":
            score,

        "confidence":
            confidence

    }

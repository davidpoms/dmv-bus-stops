"""
Ridership intelligence model.

Uses WMATA ridership metrics to create
human-readable demand intelligence.
"""

from dataclasses import dataclass


@dataclass
class RouteRidership:
    """
    Represents ridership demand for a bus route.
    """

    route_id: str
    average_daily_boardings: float
    monthly_boardings: float | None = None


    def demand_level(self):
        """
        Classify route demand based on
        average daily boardings.
        """

        if self.average_daily_boardings >= 10000:
            return "very_high"

        if self.average_daily_boardings >= 5000:
            return "high"

        if self.average_daily_boardings >= 2000:
            return "medium"

        return "low"



def calculate_demand_score(average_daily_boardings):
    """
    Convert average daily boardings
    into a 0-100 demand score.
    """

    if average_daily_boardings <= 0:
        return 0


    if average_daily_boardings >= 10000:
        return 100


    if average_daily_boardings >= 5000:
        return 85


    if average_daily_boardings >= 2000:
        return 65


    if average_daily_boardings >= 500:
        return 40


    return 20



def summarize_route(
    route_id,
    average_daily_boardings,
    monthly_boardings=None
):
    """
    Create a volunteer-friendly route summary.
    """

    route = RouteRidership(
        route_id=route_id,
        average_daily_boardings=average_daily_boardings,
        monthly_boardings=monthly_boardings
    )


    return {

        "route_id": route.route_id,

        "average_daily_boardings":
            route.average_daily_boardings,

        "monthly_boardings":
            route.monthly_boardings,

        "demand_level":
            route.demand_level(),

        "demand_score":
            calculate_demand_score(
                route.average_daily_boardings
            ),

        "source":
            "WMATA"

    }

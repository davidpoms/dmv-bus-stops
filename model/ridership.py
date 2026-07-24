"""
Ridership intelligence model.

Transforms raw route ridership data into
usable scoring information for bus stop prioritization.
"""

from dataclasses import dataclass


@dataclass
class RouteRidership:
    """
    Represents ridership demand for a bus route.
    """

    route_id: str
    monthly_boardings: float


    def demand_level(self):
        """
        Classify route demand.
        """

        if self.monthly_boardings >= 200000:
            return "very_high"

        if self.monthly_boardings >= 100000:
            return "high"

        if self.monthly_boardings >= 50000:
            return "medium"

        return "low"



def calculate_demand_score(monthly_boardings):
    """
    Convert ridership into a 0-100 score.

    Used later by priority engine.
    """

    if monthly_boardings <= 0:
        return 0


    if monthly_boardings >= 300000:
        return 100


    if monthly_boardings >= 200000:
        return 90


    if monthly_boardings >= 100000:
        return 75


    if monthly_boardings >= 50000:
        return 55


    if monthly_boardings >= 25000:
        return 35


    return 15



def summarize_route(route_id, monthly_boardings):

    route = RouteRidership(
        route_id=route_id,
        monthly_boardings=monthly_boardings
    )


    return {
        "route_id": route.route_id,
        "monthly_boardings": route.monthly_boardings,
        "demand_level": route.demand_level(),
        "demand_score": calculate_demand_score(
            route.monthly_boardings
        )
    }

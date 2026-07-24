"""
Review prioritization engine.

This module decides which bus stops should be reviewed next.

The output is not a final bench recommendation—it is simply the
optimal queue for gathering more information.
"""

from dataclasses import dataclass
from typing import Iterable

from dmv_bus_stops.models.stop import BusStop


@dataclass
class ReviewWeights:
    """
    Tunable weights for review prioritization.

    These values are intentionally simple for the initial implementation.
    They'll eventually come from a configuration file or database.
    """

    missing_bench = 30.0
    missing_shelter = 30.0

    low_confidence = 40.0

    wait_demand = 20.0

    public_requests = 25.0

    ridership = 20.0

    osm_disagreement = 35.0


class ReviewPriorityEngine:
    """
    Produces a ranked review queue.
    """

    def __init__(self, weights: ReviewWeights | None = None):

        self.weights = weights or ReviewWeights()

    def score(self, stop: BusStop) -> float:

        score = 0.0

        #
        # Missing infrastructure knowledge
        #

        if stop.has_bench is None:
            score += self.weights.missing_bench

        if stop.has_shelter is None:
            score += self.weights.missing_shelter

        #
        # Confidence
        #

        score += (
            (1.0 - stop.confidence)
            * self.weights.low_confidence
        )

        #
        # Estimated demand
        #

        if stop.estimated_wait_demand is not None:

            score += (
                stop.estimated_wait_demand
                * self.weights.wait_demand
            )

        #
        # Ridership
        #

        if hasattr(stop, "monthly_boardings"):

            score += (
                stop.monthly_boardings / 100000
            ) * self.weights.ridership

        #
        # Public requests
        #

        if hasattr(stop, "public_requests"):

            score += (
                stop.public_requests
                * self.weights.public_requests
            )

        #
        # OSM disagreement
        #

        if (
            stop.has_bench is not None
            and stop.osm_bench is not None
            and stop.has_bench != stop.osm_bench
        ):
            score += self.weights.osm_disagreement

        return score

    def rank(
        self,
        stops: Iterable[BusStop],
    ) -> list[BusStop]:

        return sorted(
            stops,
            key=self.score,
            reverse=True,
        )

    def top(
        self,
        stops: Iterable[BusStop],
        limit: int = 500,
    ) -> list[BusStop]:

        return self.rank(stops)[:limit]

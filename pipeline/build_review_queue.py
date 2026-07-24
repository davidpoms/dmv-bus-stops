"""
Review queue builder.

This is the first end-to-end pipeline in the project.

It loads bus stops, enriches them with available data, scores them,
and produces an ordered review queue.
"""

from pathlib import Path

from dmv_bus_stops.io.geojson_loader import load_geojson
from dmv_bus_stops.review.priority import ReviewPriorityEngine


class ReviewQueueBuilder:
    """
    Builds prioritized review queues.
    """

    def __init__(self):

        self.priority_engine = ReviewPriorityEngine()

    def build(
        self,
        geojson_file: str | Path,
    ):
        """
        Build a prioritized review queue.
        """

        #
        # Load WMATA stops
        #

        stops = load_geojson(geojson_file)

        #
        # Future enrichment happens here.
        #
        # Examples:
        #
        #   add OSM tags
        #   add Street View imagery
        #   add ridership
        #   add volunteer consensus
        #   add public requests
        #

        #
        # Compute review priorities
        #

        ranked = self.priority_engine.rank(stops)

        return ranked


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("geojson")

    parser.add_argument(
        "--top",
        type=int,
        default=25,
    )

    args = parser.parse_args()

    builder = ReviewQueueBuilder()

    queue = builder.build(args.geojson)

    print()

    print(f"Top {args.top} review candidates")

    print("-" * 60)

    for stop in queue[: args.top]:

        print(
            stop.stop_id,
            stop.stop_name,
            f"score={stop.review_priority:.2f}",
        )

"""
DMV Bus Stops Intelligence Platform

Nearest roadway geometry engine.

Purpose
-------
Given a bus stop location, determine:

- nearest roadway segment
- distance to roadway
- nearest point on roadway
- heading from roadway toward stop

This module contains no Google API code.
It is purely geometric.
"""

import math

import numpy as np
from scipy.spatial import cKDTree


EARTH_RADIUS_METERS = 6371000.0


def local_xy(lon, lat, lon0, lat0):
    """
    Approximate lon/lat as local Cartesian coordinates.
    Accurate enough for metropolitan-scale analysis.
    """

    x = (
        math.radians(lon - lon0)
        * EARTH_RADIUS_METERS
        * math.cos(math.radians(lat0))
    )

    y = (
        math.radians(lat - lat0)
        * EARTH_RADIUS_METERS
    )

    return x, y


def nearest_point_on_segment(
    px,
    py,
    ax,
    ay,
    bx,
    by
):
    """
    Compute the closest point on a line segment.
    """

    dx = bx - ax
    dy = by - ay

    length_sq = dx * dx + dy * dy

    if length_sq == 0:

        return ax, ay

    t = (
        ((px - ax) * dx)
        + ((py - ay) * dy)
    ) / length_sq

    t = max(0.0, min(1.0, t))

    return (
        ax + t * dx,
        ay + t * dy,
    )


class RoadSpatialIndex:
    """
    KD-tree spatial index for roadway segments.
    """

    def __init__(self, roads):

        self.edges = []

        self.edge_classes = []

        self.lon0 = None

        self.lat0 = None

        if not roads:

            self.tree = None

            return

        all_points = []

        for road in roads:

            geometry = road["geometry"]

            # Normalize coordinate nesting
            # Expected:
            # [[lon, lat], [lon, lat], ...]
            #
            # Also accepts:
            # [[[lon, lat], [lon, lat], ...]]

            if (
                geometry
                and isinstance(geometry[0], list)
                and isinstance(geometry[0][0], list)
            ):
                geometry = geometry[0]

            road["geometry"] = geometry

            all_points.extend(
                geometry
            )

        self.lon0 = (
            sum(p[0] for p in all_points)
            / len(all_points)
        )

        self.lat0 = (
            sum(p[1] for p in all_points)
            / len(all_points)
        )

        for road in roads:

            pts = [

                local_xy(
                    lon,
                    lat,
                    self.lon0,
                    self.lat0
                )

                for lon, lat
                in road["geometry"]

            ]

            for a, b in zip(pts, pts[1:]):

                self.edges.append(
                    (
                        a[0],
                        a[1],
                        b[0],
                        b[1]
                    )
                )

                self.edge_classes.append(
                    road["road_class"]
                )

        midpoints = np.array([

            (
                (e[0] + e[2]) / 2,
                (e[1] + e[3]) / 2

            )

            for e in self.edges

        ])

        self.tree = cKDTree(midpoints)

    @property
    def ready(self):

        return (
            self.tree is not None
            and len(self.edges) > 0
        )

    def nearest_road(
        self,
        lon,
        lat,
        k=8
    ):
        """
        Return the nearest roadway segment.

        Returns:

        heading
        distance
        road_class
        """

        if not self.ready:

            return None

        px, py = local_xy(
            lon,
            lat,
            self.lon0,
            self.lat0
        )

        k = min(
            k,
            len(self.edges)
        )

        _, idxs = self.tree.query(
            [px, py],
            k=k
        )

        idxs = np.atleast_1d(idxs)

        best = None

        best_dist = None

        best_class = None

        best_idx = None

        for idx in idxs:

            ax, ay, bx, by = self.edges[idx]

            qx, qy = nearest_point_on_segment(
                px,
                py,
                ax,
                ay,
                bx,
                by
            )

            dist_sq = (
                (px - qx) ** 2
                + (py - qy) ** 2
            )

            if (
                best_dist is None
                or dist_sq < best_dist
            ):

                best_dist = dist_sq

                best = (qx, qy)

                best_class = self.edge_classes[idx]

                best_idx = idx

        if best is None:

            return None

        distance = math.sqrt(best_dist)

        edge = self.edges[best_idx]

        ax, ay, bx, by = edge


        heading = (
            math.degrees(
                math.atan2(
                    bx - ax,
                    by - ay
                )
            )
            % 360
        )

        road_lon = None
        road_lat = None

        if self.lon0 is not None and self.lat0 is not None:

            road_lon = (
                self.lon0
                +
                math.degrees(
                    best[0]
                    /
                    (
                        EARTH_RADIUS_METERS
                        *
                        math.cos(math.radians(self.lat0))
                    )
                )
            )

            road_lat = (
                self.lat0
                +
                math.degrees(
                    best[1]
                    /
                    EARTH_RADIUS_METERS
                )
            )


        return {

            "heading": heading,

            "distance_m": distance,

            "road_class": best_class,

            "road_lat": road_lat,

            "road_lon": road_lon

        }


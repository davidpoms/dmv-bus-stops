"""
Load roadway centerline datasets and build a spatial index.

Unlike the original Colab notebook, this module is intended to be reused
throughout the project. It knows nothing about Street View or bus stops—it
only exposes the nearest roadway geometry.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.spatial import cKDTree


def _iter_lines(geometry):
    """
    Yield LineStrings from either LineString or MultiLineString geometries.
    """
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])

    if gtype == "LineString":
        yield coords

    elif gtype == "MultiLineString":
        yield from coords


def _local_xy(lon, lat, lon0, lat0):
    """
    Approximate geographic coordinates in meters.
    Accurate enough for neighborhood-scale nearest-neighbor searches.
    """

    R = 6371000.0

    x = math.radians(lon - lon0) * R * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * R

    return x, y


class CenterlineIndex:
    """
    Spatial index over roadway centerline segments.
    """

    def __init__(self):

        self.edges = []

        self.lon0 = None
        self.lat0 = None

        self.tree = None

    @property
    def ready(self):

        return self.tree is not None

    def load_geojson(self, filename):

        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_lines = []

        lons = []
        lats = []

        for feature in data["features"]:

            geometry = feature.get("geometry")

            if not geometry:
                continue

            for line in _iter_lines(geometry):

                clean = [(p[0], p[1]) for p in line]

                raw_lines.append(clean)

                for lon, lat in clean:

                    lons.append(lon)
                    lats.append(lat)

        if not raw_lines:
            return

        self.lon0 = sum(lons) / len(lons)
        self.lat0 = sum(lats) / len(lats)

        self.edges.clear()

        for line in raw_lines:

            pts = [
                _local_xy(lon, lat, self.lon0, self.lat0)
                for lon, lat in line
            ]

            for a, b in zip(pts, pts[1:]):

                self.edges.append((*a, *b))

        mids = np.array([
            (
                (e[0] + e[2]) / 2,
                (e[1] + e[3]) / 2,
            )
            for e in self.edges
        ])

        self.tree = cKDTree(mids)

    def load_many(self, filenames: Iterable[str | Path]):

        for filename in filenames:
            self.load_geojson(filename)

    def nearest_segments(self, lon, lat, k=10):
        """
        Return indices of the k nearest roadway segments.
        """

        if not self.ready:
            return []

        px, py = _local_xy(
            lon,
            lat,
            self.lon0,
            self.lat0,
        )

        _, idx = self.tree.query(
            [px, py],
            k=min(k, len(self.edges)),
        )

        return np.atleast_1d(idx).tolist()

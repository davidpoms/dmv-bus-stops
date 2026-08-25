"""Transparent geometry helpers for physical-stop heading audits."""

import itertools
import math


def circular_angular_separation(first, second):
    difference = abs((float(first) % 360) - (float(second) % 360))
    return min(difference, 360 - difference)


def maximum_heading_separation(headings):
    distinct = sorted({float(value) % 360 for value in headings})
    return max(
        (circular_angular_separation(a, b) for a, b in itertools.combinations(distinct, 2)),
        default=0,
    )


def strongly_contradictory(headings, threshold=135):
    """Audit classification only; it must not suppress heading evidence."""
    return maximum_heading_separation(headings) >= threshold


def distance_m(first, second):
    earth_radius = 6_371_000
    lat1, lon1 = first
    lat2, lon2 = second
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return earth_radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def connected_component_chaining(coordinates, threshold_m=20):
    """Whether a cluster connected at the threshold has diameter above it."""
    distances = [
        distance_m(a, b) for a, b in itertools.combinations(coordinates, 2)
    ]
    return bool(distances) and max(distances) > threshold_m

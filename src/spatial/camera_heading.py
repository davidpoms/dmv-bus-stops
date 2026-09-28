"""Camera bearing is independent of transit serving direction."""
import math


def bearing_to_stop(viewpoint_lat, viewpoint_lon, stop_lat, stop_lon):
    if (viewpoint_lat, viewpoint_lon) == (stop_lat, stop_lon):
        return None
    lat1, lat2 = map(math.radians, (viewpoint_lat, stop_lat))
    delta = math.radians(stop_lon - viewpoint_lon)
    return math.degrees(math.atan2(
        math.sin(delta) * math.cos(lat2),
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(delta),
    )) % 360

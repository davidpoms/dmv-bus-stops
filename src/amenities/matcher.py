import sqlite3
from math import radians, sin, cos, sqrt, atan2


def haversine_m(lat1, lon1, lat2, lon2):

    R = 6371000

    phi1 = radians(lat1)
    phi2 = radians(lat2)

    dphi = radians(lat2-lat1)
    dlambda = radians(lon2-lon1)

    a = (
        sin(dphi/2)**2
        +
        cos(phi1)
        *
        cos(phi2)
        *
        sin(dlambda/2)**2
    )

    return R * 2 * atan2(
        sqrt(a),
        sqrt(1-a)
    )


def find_nearest_physical_stop(
    db,
    latitude,
    longitude,
    jurisdiction_state=None,
    maximum_distance_m=100,
):

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT
            id,
            latitude,
            longitude,
            state
        FROM physical_stops
    """
    parameters = ()

    if jurisdiction_state is not None:
        query += " WHERE state = ?"
        parameters = (jurisdiction_state,)

    stops = conn.execute(query, parameters)

    best = None
    best_distance = None

    for stop in stops:

        distance = haversine_m(
            latitude,
            longitude,
            stop["latitude"],
            stop["longitude"]
        )

        if best_distance is None or distance < best_distance:
            best_distance = distance
            best = stop

    conn.close()

    if best is None:
        return None


    if best_distance > maximum_distance_m:
        return None

    if best_distance <= 10:
        confidence = "high"
    elif best_distance <= 50:
        confidence = "medium"
    elif best_distance <= 100:
        confidence = "low"
    else:
        confidence = "out_of_range"
    return {
        "physical_stop_id": best["id"],
        "distance_m": best_distance,
        "confidence": confidence,
        "state": best["state"],
    }

def find_nearest_wmata_stop(
    db,
    latitude,
    longitude
):

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    stops = conn.execute(
        """
        SELECT
            p.id,
            p.latitude,
            p.longitude,
            w.wmata_stop_id
        FROM physical_stops p
        JOIN stop_wmata_evidence w
        ON p.id = w.physical_stop_id
        GROUP BY p.id
        """
    )

    best = None
    best_distance = None

    for stop in stops:

        distance = haversine_m(
            latitude,
            longitude,
            stop["latitude"],
            stop["longitude"]
        )

        if (
            best_distance is None
            or distance < best_distance
        ):
            best_distance = distance
            best = stop

    conn.close()

    if best is None:
        return None

    if best_distance <= 15:
        confidence = "high"
    elif best_distance <= 50:
        confidence = "medium"
    elif best_distance <= 100:
        confidence = "low"
    else:
        return None

    return {
        "physical_stop_id": best["id"],
        "wmata_stop_id": best["wmata_stop_id"],
        "distance_m": best_distance,
        "confidence": confidence
    }

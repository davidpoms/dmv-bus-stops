from pathlib import Path

FILE = Path("src/amenities/matcher.py")

text = FILE.read_text()

addition = r'''

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
'''

if "def find_nearest_wmata_stop" not in text:
    text += addition

FILE.write_text(text)

print("Added WMATA-only amenity matcher")
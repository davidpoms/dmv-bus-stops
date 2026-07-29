from pathlib import Path

FILE = Path("scripts/import_wmata_evidence.py")

text = FILE.read_text()

old = """rows = []


for _, w in wmata.iterrows():

    best_id = None
    best_distance = None

    for _, p in physical.iterrows():

        d = distance_m(
            w.lat,
            w.lon,
            p.latitude,
            p.longitude
        )

        if best_distance is None or d < best_distance:
            best_distance = d
            best_id = p.id


    rows.append(
        (
            best_id,
            int(w.stop_id),
            w.wmata_status,
            int(w.heading),
            w.wmata_bench,
            w.wmata_shelter,
            w.wmata_accessible,
            float(best_distance),
            confidence(best_distance),
            "WMATA"
        )
    )
"""

new = """from scipy.spatial import cKDTree
import numpy as np


rows = []

# Build spatial index once instead of comparing every WMATA stop
# against every physical stop.
physical_coords = physical[["latitude", "longitude"]].values

tree = cKDTree(physical_coords)

wmata_coords = wmata[["lat", "lon"]].values

distances, indexes = tree.query(
    wmata_coords,
    k=1
)

physical_ids = physical["id"].values


for i, (_, w) in enumerate(wmata.iterrows()):

    best_id = int(physical_ids[indexes[i]])

    # Convert approximate degree distance to meters
    best_distance = float(distances[i] * 111320)

    rows.append(
        (
            best_id,
            int(w.stop_id),
            w.wmata_status,
            int(w.heading),
            w.wmata_bench,
            w.wmata_shelter,
            w.wmata_accessible,
            best_distance,
            confidence(best_distance),
            "WMATA"
        )
    )
"""

if old not in text:
    raise Exception(
        "Could not find old brute-force matching block. "
        "Importer may already be patched or changed."
    )

text = text.replace(old, new)

FILE.write_text(text)

print("Patched import_wmata_evidence.py with KD-tree matching")

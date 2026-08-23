import pandas as pd


DCGIS = "data/dcgis_wmata_stops.csv"
WMATA = "data/wmata_bus_stops_raw.csv"


print("Loading datasets...")

dc = pd.read_csv(DCGIS)
wmata = pd.read_csv(WMATA)


# Normalize IDs
dc["BSTP_GEO_ID"] = dc["BSTP_GEO_ID"].astype(str)
wmata["BSTP_GEO_ID"] = wmata["BSTP_GEO_ID"].astype(str)


dc_ids = set(dc["BSTP_GEO_ID"])
wmata_ids = set(wmata["BSTP_GEO_ID"])


print()
print("========== COUNTS ==========")
print("DCGIS records:", len(dc))
print("DCGIS unique stops:", len(dc_ids))

print()

print("WMATA records:", len(wmata))
print("WMATA unique stops:", len(wmata_ids))


print()
print("========== OVERLAP ==========")

print(
    "Shared stop IDs:",
    len(dc_ids & wmata_ids)
)

print(
    "Only DCGIS:",
    len(dc_ids - wmata_ids)
)

print(
    "Only WMATA:",
    len(wmata_ids - dc_ids)
)


print()
print("========== DCGIS STATUS ==========")

print(
    dc["BSTP_OPS_TCD"]
    .value_counts(dropna=False)
)


print()
print("========== WMATA STATUS ==========")

print(
    wmata["BSTP_OPS_TCD"]
    .value_counts(dropna=False)
)


# Compare only shared stops
shared = list(dc_ids & wmata_ids)

dc_shared = dc[
    dc.BSTP_GEO_ID.isin(shared)
].copy()

wm_shared = wmata[
    wmata.BSTP_GEO_ID.isin(shared)
].copy()


print()
print("========== LOCATION DIFFERENCES ==========")


merged = dc_shared.merge(
    wm_shared,
    on="BSTP_GEO_ID",
    suffixes=("_dcgis","_wmata")
)


merged["lat_diff_m"] = (
    (merged.BSTP_LAT_dcgis -
     merged.BSTP_LAT_wmata)
    * 111000
)

merged["lon_diff_m"] = (
    (merged.BSTP_LON_dcgis -
     merged.BSTP_LON_wmata)
    * 85000
)


merged["distance_difference_m"] = (
    merged["lat_diff_m"]**2 +
    merged["lon_diff_m"]**2
)**0.5


print(
    merged[
        "distance_difference_m"
    ].describe()
)


print()
print("Stops >10m apart:")

print(
    (
        merged.distance_difference_m > 10
    ).sum()
)


print()
print("Example differences:")

print(
    merged[
        [
            "BSTP_GEO_ID",
            "BSTP_MSG_TEXT_dcgis",
            "BSTP_MSG_TEXT_wmata",
            "distance_difference_m"
        ]
    ]
    .sort_values(
        "distance_difference_m",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)


# Save comparison
merged.to_csv(
    "data/wmata_dcgis_stop_comparison.csv",
    index=False
)

print()
print(
    "Saved:",
    "data/wmata_dcgis_stop_comparison.csv"
)

import pandas as pd
from pathlib import Path


INPUT = Path("data/wmata_bus_stops_clean.csv")
OUTPUT = Path("data/wmata_stops_pipeline.csv")


df = pd.read_csv(INPUT)

out = pd.DataFrame()

# Identity
out["stop_id"] = df["BSTP_GEO_ID"]

# Location
out["lat"] = df["BSTP_LAT"]
out["lon"] = df["BSTP_LON"]

# Agency information
out["source"] = "WMATA"
out["source_confidence"] = "high"

# Street information
out["street"] = df["AT_STR"]
out["cross_street"] = df["ON_STR"]

# Existing WMATA accessibility indicators
out["wmata_bench"] = df["BSTP_HAS_BKRS"]
out["wmata_shelter"] = df["BSTP_HAS_PRS"]
out["wmata_accessible"] = df["BSTP_ACC_RATING"]

# Sidewalk width
out["sidewalk_width_ft"] = df["BSTP_SWK_WDT"]

# Direction
out["heading"] = df["BSTP_HDG"]

# Operational status
out["wmata_status"] = df["BSTP_OPS_TCD"]


out.to_csv(OUTPUT, index=False)

print("Saved:", OUTPUT)
print("Rows:", len(out))
print()
print(out.head())

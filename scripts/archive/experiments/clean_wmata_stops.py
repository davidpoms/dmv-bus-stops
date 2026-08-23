import pandas as pd
from pathlib import Path

INPUT = Path("data/wmata_bus_stops_raw.csv")
OUTPUT = Path("data/wmata_bus_stops_clean.csv")


df = pd.read_csv(INPUT)

print("Raw rows:", len(df))


# Keep useful fields that exist
wanted = [
    "BSTP_GEO_ID",
    "BSTP_OPS_TCD",
    "BSTP_LAT",
    "BSTP_LON",
    "BSTP_HDG",
    "AT_STR",
    "ON_STR",
    "BSTP_HAS_BKRS",
    "BSTP_HAS_PRS",
    "BSTP_ACC_RATING",
    "BSTP_SWK_WDT",
]

existing = [c for c in wanted if c in df.columns]

df = df[existing].copy()


# Normalize coordinates
for col in ["BSTP_LAT", "BSTP_LON", "BSTP_HDG", "BSTP_SWK_WDT"]:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


# Convert Y/N flags safely
for col in ["BSTP_HAS_BKRS", "BSTP_HAS_PRS"]:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.upper()
            .map({
                "Y": True,
                "N": False,
                "YES": True,
                "NO": False
            })
        )


# Clean duplicate stops
before = len(df)

if "BSTP_GEO_ID" in df.columns:
    df = df.drop_duplicates(
        subset=["BSTP_GEO_ID"]
    )

print("Removed duplicates:", before - len(df))


# Remove missing coordinates
if {"BSTP_LAT","BSTP_LON"}.issubset(df.columns):
    before = len(df)

    df = df.dropna(
        subset=["BSTP_LAT","BSTP_LON"]
    )

    print(
        "Removed missing coordinates:",
        before-len(df)
    )


df.to_csv(
    OUTPUT,
    index=False
)


print("Saved:", OUTPUT)
print("Rows:", len(df))

import sqlite3
import pandas as pd
from pathlib import Path


DB = "src/database/dmv_bus_stops.db"

INPUT = Path("data/wmata_dcgis_stop_comparison.csv")


df = pd.read_csv(INPUT, low_memory=False)

print("Records:", len(df))


retired = df[
    df["BSTP_TCD"]
    .astype(str)
    .isin(["REV", "DEL", "DUM", "IDL"])
].copy()


print("Retired WMATA records:", len(retired))


conn = sqlite3.connect(DB)


conn.execute(
    "DELETE FROM wmata_retirement_evidence"
)


rows = []

for _, r in retired.iterrows():

    rows.append(
        (
            str(r.get("REG_ID_wmata", "")),
            str(r.get("BSTP_GEO_ID", "")),
            str(r.get("BSTP_TCD", "")),
            str(r.get("BSTP_EFF_DATE_wmata", "")),
            str(r.get("AT_STR_wmata", "")),
            str(r.get("ON_STR_wmata", "")),
            f"{r.get('ON_STR_wmata','')} + {r.get('AT_STR_wmata','')}",
            float(r["BSTP_LAT_wmata"]),
            float(r["BSTP_LON_wmata"]),
            str(r.get("BSTP_MSG_TEXT_wmata", "")),
            "WMATA DCGIS"
        )
    )


conn.executemany(
"""
INSERT INTO wmata_retirement_evidence
(
wmata_stop_id,
dcgis_stop_id,
status_code,
effective_date,
street,
cross_street,
stop_name,
latitude,
longitude,
note,
source
)
VALUES (?,?,?,?,?,?,?,?,?,?,?)
""",
rows
)


conn.commit()
conn.close()


print("Inserted retirement evidence:", len(rows))

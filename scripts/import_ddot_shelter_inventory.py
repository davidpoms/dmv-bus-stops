import sqlite3
from pathlib import Path
import pandas as pd


DB = Path("src/database/dmv_bus_stops.db")
INPUT = Path("data/ddot_shelter_inventory.xlsx")


conn = sqlite3.connect(DB)


print("Loading spreadsheet...")
df = pd.read_excel(INPUT)


print("Columns:")
for c in df.columns:
    print(c)


print()
print("Rows:", len(df))


# Normalize column names
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("?", "")
)


print("\nNormalized columns:")
print(df.columns.tolist())


# Create evidence table

conn.execute("""
CREATE TABLE IF NOT EXISTS ddot_shelter_inventory (

    id INTEGER PRIMARY KEY,

    panel_id TEXT,
    sales_address TEXT,
    zip_code TEXT,
    quad TEXT,

    shelter_type TEXT,
    illuminated TEXT,

    ddot_id TEXT,

    photos TEXT,
    notes TEXT,

    source TEXT DEFAULT 'DDOT',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")


rows = []

for _, r in df.iterrows():

    rows.append(
        (
            str(r.get("panel")),
            r.get("sales_address"),
            r.get("zip_code"),
            r.get("quad"),
            r.get("shelter_type"),
            r.get("illuminated"),
            str(r.get("ddot_id")),
            r.get("photos"),
            r.get("notes"),
        )
    )


conn.executemany(
"""
INSERT INTO ddot_shelter_inventory
(
panel_id,
sales_address,
zip_code,
quad,
shelter_type,
illuminated,
ddot_id,
photos,
notes
)

VALUES (?,?,?,?,?,?,?,?,?)

""",
rows
)


conn.commit()


print()
print("Inserted DDOT shelters:", len(rows))


print(
    conn.execute(
        """
        SELECT COUNT(*)
        FROM ddot_shelter_inventory
        """
    ).fetchone()
)


conn.close()
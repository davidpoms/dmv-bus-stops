"""QUARANTINED importer for unsafe legacy DDOT reconciliation output.

The implementation remains below for auditability. Execution is disabled
before files or the database are opened.
"""

raise SystemExit(
    "QUARANTINED LEGACY PATH: importing DDOT route reconciliation is disabled. "
    "Historical stop_ddot_shelter_evidence rows are retained for audit only."
)

import sqlite3
import pandas as pd
from datetime import datetime


DB = "src/database/dmv_bus_stops.db"

INPUT = "ddot_route_evidence_reconciliation.csv"


def main():

    print("Loading reconciliation...")

    df = pd.read_csv(INPUT)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()


    print("Creating table...")


    cur.execute("""
    CREATE TABLE IF NOT EXISTS stop_ddot_shelter_evidence (

        id INTEGER PRIMARY KEY,

        physical_stop_id INTEGER NOT NULL,

        ddot_id TEXT,

        api_id TEXT,

        lifecycle_status TEXT,

        route_ids TEXT,

        route_count INTEGER,

        confidence TEXT,

        notes TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )
    """)


    print("Clearing existing DDOT evidence...")

    cur.execute("""
        DELETE FROM stop_ddot_shelter_evidence
    """)


    inserted = 0


    for _, row in df.iterrows():

        physical_ids = str(row["physical_stop_ids"])

        if physical_ids == "nan":
            continue


        ids = [
            x.strip()
            for x in physical_ids.split(",")
        ]


        for physical_id in ids:

            cur.execute(
                """
                INSERT INTO stop_ddot_shelter_evidence
                (
                    physical_stop_id,
                    ddot_id,
                    api_id,
                    lifecycle_status,
                    route_ids,
                    route_count,
                    confidence,
                    notes
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)

                """,
                (

                    int(physical_id),

                    str(row["spreadsheet_id"]),

                    None
                    if pd.isna(row["api_id"])
                    else str(row["api_id"]),


                    row["route_evidence_status"],


                    row["routes"],


                    int(row["route_count"])
                    if not pd.isna(row["route_count"])
                    else 0,


                    (
                        "high"
                        if row["route_evidence_status"]
                        in [
                            "CONFIRMED_ACTIVE",
                            "ROUTE_PRESENT"
                        ]
                        else "medium"
                    ),


                    (
                        "DDOT procurement shelter inventory. "
                        f"Lifecycle status: {row['route_evidence_status']}."
                    )

                )
            )


            inserted += 1


    conn.commit()
    conn.close()


    print()
    print("Inserted DDOT evidence:", inserted)


if __name__ == "__main__":
    main()

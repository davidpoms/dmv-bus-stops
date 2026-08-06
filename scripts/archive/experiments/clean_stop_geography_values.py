from pathlib import Path
import sqlite3


DB = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


def main():

    conn = sqlite3.connect(DB)

    # Clean DC ward formatting
    conn.execute(
        """
        UPDATE physical_stops
        SET dc_ward = CAST(dc_ward AS INTEGER)
        WHERE dc_ward IS NOT NULL
        """
    )


    # Clear non-DC geography fields
    conn.execute(
        """
        UPDATE physical_stops
        SET
            county = NULL,
            municipality = NULL
        WHERE state='DC'
        """
    )


    # Normalize ANC formatting
    conn.execute(
        """
        UPDATE physical_stops
        SET dc_anc = UPPER(TRIM(dc_anc))
        WHERE dc_anc IS NOT NULL
        """
    )


    conn.commit()
    conn.close()

    print("Cleaned geography values")


if __name__ == "__main__":
    main()

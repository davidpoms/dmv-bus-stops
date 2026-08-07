import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)


cursor = conn.execute(
    """
    UPDATE stop_amenity_evidence

    SET jurisdiction='MONTGOMERY_COUNTY'

    WHERE source='MONTGOMERY_COUNTY'
    AND jurisdiction IS NULL
    """
)


print("Updated:", cursor.rowcount)


conn.commit()
conn.close()
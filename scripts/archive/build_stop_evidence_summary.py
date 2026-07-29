import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)


conn.execute("""
CREATE TABLE IF NOT EXISTS stop_wmata_history_summary (

    physical_stop_id INTEGER PRIMARY KEY,

    has_retirement_history INTEGER DEFAULT 0,

    retirement_count INTEGER DEFAULT 0,

    latest_status TEXT,

    statuses TEXT,

    high_confidence_count INTEGER DEFAULT 0,

    medium_confidence_count INTEGER DEFAULT 0

)
""")


conn.execute(
"DELETE FROM stop_wmata_history_summary"
)


conn.execute("""
INSERT INTO stop_wmata_history_summary
(
physical_stop_id,
has_retirement_history,
retirement_count,
latest_status,
statuses,
high_confidence_count,
medium_confidence_count
)

SELECT

    physical_stop_id,

    1,

    COUNT(*),

    GROUP_CONCAT(status_code),

    GROUP_CONCAT(DISTINCT status_code),

    SUM(
        CASE
            WHEN confidence='high'
            THEN 1
            ELSE 0
        END
    ),

    SUM(
        CASE
            WHEN confidence='medium'
            THEN 1
            ELSE 0
        END
    )

FROM wmata_retirement_links

WHERE confidence IN ('high','medium')

GROUP BY physical_stop_id

""")


conn.commit()


print(
    conn.execute(
        """
        SELECT COUNT(*)
        FROM stop_wmata_history_summary
        """
    ).fetchone()[0],
    "physical stops with WMATA history"
)


conn.close()

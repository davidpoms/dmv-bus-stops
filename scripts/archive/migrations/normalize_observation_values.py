"""
Normalize stop_observations fields into consistent values.
"""

import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


# Normalize bench_present

cur.execute(
    """
    UPDATE stop_observations
    SET bench_present =
        CASE

            WHEN LOWER(TRIM(bench_present))
                IN ('yes','true','1')
            THEN '1'

            WHEN LOWER(TRIM(bench_present))
                IN ('no','false','0')
            THEN '0'

            ELSE bench_present

        END
    """
)


# Normalize bench_feasible

cur.execute(
    """
    UPDATE stop_observations
    SET bench_feasible =
        CASE

            WHEN LOWER(TRIM(bench_feasible))
                IN ('yes','true','1')
            THEN '1'

            WHEN LOWER(TRIM(bench_feasible))
                IN ('no','false','0')
            THEN '0'

            ELSE bench_feasible

        END
    """
)


# Normalize ADA

cur.execute(
    """
    UPDATE stop_observations
    SET ada_clearance_possible =
        CASE

            WHEN LOWER(TRIM(ada_clearance_possible))
                IN ('yes','true','1')
            THEN '1'

            WHEN LOWER(TRIM(ada_clearance_possible))
                IN ('no','false','0')
            THEN '0'

            ELSE ada_clearance_possible

        END
    """
)


conn.commit()


print("Observation values normalized")


conn.close()

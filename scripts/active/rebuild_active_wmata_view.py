import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)


conn.execute("""
DROP VIEW IF EXISTS active_wmata_evidence;
""")


conn.execute("""
CREATE VIEW active_wmata_evidence AS

SELECT *

FROM (

    SELECT
        swe.*,

        ROW_NUMBER() OVER(
            PARTITION BY physical_stop_id

            ORDER BY

                CASE
                    WHEN wmata_status='PRS'
                    THEN 0
                    ELSE 1
                END,

                match_distance_m ASC

        ) AS rn


    FROM stop_wmata_evidence swe

)

WHERE rn=1;

""")


conn.commit()
conn.close()


print("Rebuilt active_wmata_evidence view")
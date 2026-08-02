import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute("""
DROP VIEW IF EXISTS active_wmata_evidence;
""")


cur.execute("""
CREATE VIEW active_wmata_evidence AS

SELECT *

FROM stop_wmata_evidence

WHERE
    wmata_status='PRS'
    OR wmata_status IS NULL;

""")


conn.commit()

print("Created active_wmata_evidence view")


conn.close()
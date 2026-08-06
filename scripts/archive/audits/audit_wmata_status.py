import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


print("\nWMATA STATUS COUNTS")
print("-------------------")

for row in cur.execute("""
    SELECT
        wmata_status,
        COUNT(*)
    FROM stop_wmata_evidence
    GROUP BY wmata_status
    ORDER BY COUNT(*) DESC
"""):
    print(row)


print("\nACTIVE STOPS WITH SHELTER")
print("-------------------------")

for row in cur.execute("""
    SELECT
        COUNT(*)
    FROM stop_wmata_evidence
    WHERE wmata_status='PRS'
    AND wmata_shelter=1
"""):
    print(row[0])


print("\nABS STOPS WITH SHELTER")
print("----------------------")

for row in cur.execute("""
    SELECT
        COUNT(*)
    FROM stop_wmata_evidence
    WHERE wmata_status='ABS'
    AND wmata_shelter=1
"""):
    print(row[0])


conn.close()
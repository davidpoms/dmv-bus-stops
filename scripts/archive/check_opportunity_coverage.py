import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)
c=conn.cursor()

print("Physical stops:")
print(c.execute(
"""
SELECT COUNT(*)
FROM physical_stops
"""
).fetchone()[0])


print("Opportunity assessments:")
print(c.execute(
"""
SELECT COUNT(*)
FROM opportunity_assessments
"""
).fetchone()[0])


print("Improvement opportunities:")
print(c.execute(
"""
SELECT COUNT(*)
FROM improvement_opportunities
"""
).fetchone()[0])


print("Stops without assessments:")

print(c.execute(
"""
SELECT COUNT(*)
FROM physical_stops ps
LEFT JOIN opportunity_assessments oa
ON oa.physical_stop_id = ps.id
WHERE oa.physical_stop_id IS NULL
"""
).fetchone()[0])
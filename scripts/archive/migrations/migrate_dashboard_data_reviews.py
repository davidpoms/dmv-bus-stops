from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

replacements = {

"COUNT(sr.id) AS review_count":
"COUNT(o.id) AS review_count",

"AVG(sr.reviewer_confidence)\n                AS confidence":
"AVG(o.confidence)\n                AS confidence",

"LEFT JOIN stop_reviews sr\n            ON ps.id = sr.stop_id":
"LEFT JOIN stop_observations o\n            ON ps.id = o.physical_stop_id",

"FROM stop_reviews\n                WHERE has_bench = 1":
"FROM stop_observations\n                WHERE bench_present='yes'",

"FROM stop_reviews\n                WHERE has_bench = 0\n                AND bench_location_feasible = 1":
"FROM stop_observations\n                WHERE bench_present='no'\n                AND bench_feasible='yes'",

"FROM stop_reviews\n\n            GROUP BY stop_id":
"FROM stop_observations\n\n            GROUP BY physical_stop_id",

"SELECT stop_id\n                            FROM stop_reviews":
"SELECT physical_stop_id\n                            FROM stop_observations",

"SELECT COUNT(DISTINCT stop_id)\n                FROM stop_reviews":
"SELECT COUNT(DISTINCT physical_stop_id)\n                FROM stop_observations",

"SELECT stop_id\n                    FROM stop_reviews":
"SELECT physical_stop_id\n                    FROM stop_observations",

"GROUP BY stop_id\n                    HAVING COUNT(\n                        DISTINCT COALESCE(\n                            reviewer_id,\n                            CAST(user_id AS TEXT),\n                            anonymous_email\n                        )":
"GROUP BY physical_stop_id\n                    HAVING COUNT(\n                        DISTINCT COALESCE(\n                            reviewer_id,\n                            observer\n                        )",

}

for old,new in replacements.items():
    text = text.replace(old,new)

p.write_text(text)

print("Migrated dashboard data queries to stop_observations")

#!/bin/bash

set -e

FILE="src/assessment/score_improvement_opportunities.py"

python - <<'PY'
from pathlib import Path

path = Path("src/assessment/score_improvement_opportunities.py")

text = path.read_text()

text = text.replace(
'''        ridership_score = normalize(
            total_daily,
            max_daily
        )


        route_score = normalize(
            routes,
            max_routes
        )


        complexity_score = normalize(
            records,
            max_records
        )


        opportunity_score = (

            ridership_score * 0.70

            +

            route_score * 0.25

            +

            complexity_score * 0.05

        )
''',
'''        route_exposure_score = normalize(
            total_daily,
            max_daily
        )


        connectivity_score = normalize(
            routes,
            max_routes
        )


        physical_complexity_score = normalize(
            records,
            max_records
        )


        opportunity_score = (

            route_exposure_score * 0.70

            +

            connectivity_score * 0.25

            +

            physical_complexity_score * 0.05

        )
'''
)

text = text.replace(
'''            "ridership": {

                "total_daily_weekday_boardings":
                    round(
                        total_daily,
                        2
                    ),

                "highest_route_daily_boardings":
                    round(
                        highest_route,
                        2
                    )

            },
''',
'''            "route_exposure": {

                "combined_route_weekday_boardings":
                    round(
                        total_daily,
                        2
                    ),

                "highest_route_weekday_boardings":
                    round(
                        highest_route,
                        2
                    ),

                "note":
                    "Route-level ridership exposure, not stop-level passenger counts"

            },
'''
)

text = text.replace(
'''            "network": {

                "routes_served":
                    routes

            },
''',
'''            "network": {

                "routes_served":
                    routes,

                "transfer_candidate":
                    routes >= 3

            },
'''
)

path.write_text(text)

print("Updated score_improvement_opportunities.py")
PY

python -m py_compile "$FILE"

echo "Syntax check passed."

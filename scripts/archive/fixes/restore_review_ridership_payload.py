from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = '''            "impact_summary":
                {
                    "rider_exposure_percentile":
                        rider_exposure_percentile
                }
'''


new = '''            "impact_summary":
                {
                    "rider_exposure_percentile":
                        rider_exposure_percentile,

                    "estimated_weekday_boardings":
                        ridership_exposure["average_weekday_boardings"]
                        if ridership_exposure
                        else None,

                    "routes_served":
                        ridership_exposure["route_count"]
                        if ridership_exposure
                        else 0,

                    "routes":
                        ridership_exposure["routes"]
                        if ridership_exposure
                        else []
                }
'''


if old not in text:
    raise Exception(
        "Could not find impact_summary block"
    )


text = text.replace(
    old,
    new
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Restored review ridership payload"
)
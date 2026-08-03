from pathlib import Path

app = Path("src/api/app.py")

text = app.read_text(encoding="utf-8")

marker = """    ridership_exposure = (
        {
            "weekday_boardings_total":
"""

insert = """
    rider_exposure = query_db(
        '''
        SELECT
            assessment_json

        FROM opportunity_assessments

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )

    rider_exposure_percentile = None

    if rider_exposure and rider_exposure[0][0]:

        try:

            assessment = json.loads(
                rider_exposure[0][0]
            )

            rider_exposure_percentile = (
                assessment.get(
                    "rider_exposure_percentile"
                )
            )

        except Exception:

            pass


"""

if "rider_exposure_percentile = None" in text[:text.find("@app.route(\"/review/start\")")]:
    print("Patch already applied.")
    raise SystemExit()

location = text.find(marker)

if location == -1:
    raise RuntimeError("Couldn't locate ridership block.")

text = (
    text[:location]
    + insert
    + text[location:]
)

app.write_text(text, encoding="utf-8")

print("Restored dashboard percentile calculation.")
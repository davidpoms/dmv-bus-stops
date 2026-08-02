from pathlib import Path
import shutil


TARGET = Path(
    "src/assessment/generate_impact_summary.py"
)

BACKUP = TARGET.with_suffix(
    ".backup_rider_exposure"
)


OLD = '''        summary = (
            f"Bus stop with "
            f"{round(daily_route_exposure):,} combined weekday boardings across serving routes."
        )


        if recommendation_list:
'''


NEW = '''        summary = (
            f"Bus stop with "
            f"{round(daily_route_exposure):,} combined weekday boardings across serving routes."
        )


        percentile = assessment.get(
            "rider_exposure_percentile"
        )


        if percentile:

            if percentile >= 95:

                summary += (
                    " This stop is among the highest "
                    "rider exposure stops in the Metrobus network."
                )

            elif percentile >= 90:

                summary += (
                    f" This stop is in the top "
                    f"{100-percentile}% of Metrobus stops "
                    "by rider exposure."
                )

            else:

                summary += (
                    f" This stop ranks in the "
                    f"{percentile}th percentile "
                    "for rider exposure."
                )


        if recommendation_list:
'''


text = TARGET.read_text(
    encoding="utf-8"
)


if OLD not in text:
    raise Exception(
        "Could not find target summary block. File may have changed."
    )


print("Creating backup...")
shutil.copy2(
    TARGET,
    BACKUP
)


text = text.replace(
    OLD,
    NEW
)


TARGET.write_text(
    text,
    encoding="utf-8"
)


print("Updated impact summary generator.")
print(f"Backup: {BACKUP}")
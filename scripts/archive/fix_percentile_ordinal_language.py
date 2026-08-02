from pathlib import Path
import shutil


TARGET = Path(
    "src/assessment/generate_impact_summary.py"
)

BACKUP = TARGET.with_suffix(
    ".backup_percentile_ordinal"
)


OLD = '''                summary += (
                    f" This stop ranks in the "
                    f"{percentile}th percentile "
                    "for rider exposure."
                )
'''


NEW = '''                if percentile % 100 in (11, 12, 13):

                    suffix = "th"

                else:

                    suffix = {
                        1: "st",
                        2: "nd",
                        3: "rd"
                    }.get(
                        percentile % 10,
                        "th"
                    )


                summary += (
                    f" This stop ranks in the "
                    f"{percentile}{suffix} percentile "
                    "for rider exposure."
                )
'''


text = TARGET.read_text(
    encoding="utf-8"
)


if OLD not in text:
    raise Exception(
        "Could not find percentile wording block."
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


print("Fixed percentile ordinal wording.")
print(f"Backup: {BACKUP}")
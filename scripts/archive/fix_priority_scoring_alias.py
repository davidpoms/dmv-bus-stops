from pathlib import Path
import shutil


TARGET = Path(
    "src/scoring/calculate_stop_priority.py"
)

BACKUP = TARGET.with_suffix(
    ".py.alias_backup"
)


def main():

    shutil.copy(
        TARGET,
        BACKUP
    )

    text = TARGET.read_text(
        encoding="utf-8"
    )


    replacements = {
        "b.id": "ps.id"
    }


    for old, new in replacements.items():

        count = text.count(old)

        print(
            f"Replacing {old}: {count}"
        )

        text = text.replace(
            old,
            new
        )


    TARGET.write_text(
        text,
        encoding="utf-8"
    )


    print(
        "Alias fix complete"
    )


if __name__ == "__main__":
    main()
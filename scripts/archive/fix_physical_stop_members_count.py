from pathlib import Path


FILE = Path(
    "src/assessment/create_opportunity_assessments.py"
)


def main():

    text = FILE.read_text(
        encoding="utf-8"
    )


    text = text.replace(
        "COUNT(pm.id)",
        "COUNT(pm.bus_stop_id)"
    )


    FILE.write_text(
        text,
        encoding="utf-8"
    )


    print(
        "Fixed physical_stop_members count"
    )


if __name__ == "__main__":
    main()
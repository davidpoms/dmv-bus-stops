import pandas as pd
from clients.gtfs_loader import download_gtfs

gtfs = download_gtfs()

stops = pd.read_csv(gtfs.open("stops.txt"))

for col in stops.columns:
    matches = stops[
        stops[col]
        .astype(str)
        .str.contains(
            "12913|12915|2005490|NORWOOD",
            regex=True,
            case=False
        )
    ]

    if len(matches):
        print("\nMATCH COLUMN:", col)
        print(matches.head(10))
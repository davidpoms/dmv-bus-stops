import geopandas as gpd
from pathlib import Path


OUT = Path("data/geography")
OUT.mkdir(parents=True, exist_ok=True)


# Counties
counties = gpd.read_file(
    "https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip"
)

counties = counties[
    counties.STATEFP.isin([
        "24", # Maryland
        "51"  # Virginia
    ])
]

counties.to_file(
    OUT/"md_va_counties.geojson",
    driver="GeoJSON"
)


# Places
places = gpd.read_file(
    "https://www2.census.gov/geo/tiger/TIGER2025/PLACE/tl_2025_24_place.zip"
)

places = places[
    places.STATEFP=="24"
]

places.to_file(
    OUT/"md_places.geojson",
    driver="GeoJSON"
)


places = gpd.read_file(
    "https://www2.census.gov/geo/tiger/TIGER2025/PLACE/tl_2025_51_place.zip"
)

places.to_file(
    OUT/"va_places.geojson",
    driver="GeoJSON"
)


print("Finished")

"""
DMV Bus Stops Intelligence Platform

Road centerline ingestion.

Purpose:
- Load roadway GeoJSON files
- Support multiple jurisdictions
- Extract usable line geometry
- Preserve road classification

Sources may include:
- DC Roadway Block
- Maryland Road Centerlines
- Virginia regional centerlines

This module prepares data for:
nearest road matching,
camera heading calculations,
and accessibility analysis.
"""


import json
from pathlib import Path



# ------------------------------------------------------------
# Road classification fields
#
# Different jurisdictions use different names.
# ------------------------------------------------------------

ROAD_CLASS_FIELDS = [

    "FHWAFUNCTIONALCLASS",

    "DCFUNCTIONALCLASS",

    "CFCC",

    "fcc",

    "ROAD_CLASS",

    "FFX_CLASS"

]




def extract_road_class(properties):

    """
    Find available road classification metadata.
    """

    for field in ROAD_CLASS_FIELDS:

        value = properties.get(field)


        if value not in (None, ""):

            return {
                "field": field,
                "value": value
            }


    return None





def iter_lines(geometry):

    """
    Normalize LineString and MultiLineString.

    Returns:
    list of coordinate arrays
    """

    if not geometry:

        return



    geometry_type = geometry.get(
        "type"
    )


    coordinates = geometry.get(
        "coordinates",
        []
    )


    if geometry_type == "LineString":

        yield coordinates



    elif geometry_type == "MultiLineString":


        for line in coordinates:

            yield line





def load_centerlines(filepath):

    """
    Load a single roadway GeoJSON file.

    Returns:

    [
        {
            geometry:
                [(lon,lat),(lon,lat)],

            road_class:
                {...}
        }
    ]

    """

    filepath = Path(filepath)


    if not filepath.exists():

        raise FileNotFoundError(
            f"Centerline file not found: {filepath}"
        )



    with open(
        filepath,
        "r",
        encoding="utf-8"
    ) as f:

        geojson = json.load(f)



    roads = []



    for feature in geojson.get(
        "features",
        []
    ):


        geometry = feature.get(
            "geometry"
        )


        properties = feature.get(
            "properties",
            {}
        )



        road_class = extract_road_class(
            properties
        )



        for line in iter_lines(geometry):


            cleaned = [

                (
                    point[0],
                    point[1]
                )

                for point in line

            ]



            roads.append(

                {

                    "geometry": cleaned,

                    "road_class": road_class

                }

            )



    return roads





def load_multiple_centerlines(files):

    """
    Load several jurisdictions together.

    Example:

    [
        "dc_roads.geojson",
        "maryland_roads.geojson",
        "virginia_roads.geojson"
    ]

    """

    all_roads = []


    for filepath in files:


        roads = load_centerlines(
            filepath
        )


        print(
            f"{filepath}: "
            f"{len(roads)} road features"
        )


        all_roads.extend(
            roads
        )



    return all_roads





def summarize_centerlines(roads):

    """
    Basic data quality check.
    """

    print(
        f"Loaded {len(roads)} road geometries"
    )


    classified = sum(

        1
        for r in roads
        if r["road_class"]

    )


    print(
        f"Roads with classification: "
        f"{classified}"
    )





if __name__ == "__main__":

    import sys


    files = sys.argv[1:]


    if not files:

        print(
            "Provide centerline GeoJSON files"
        )

        exit()



    roads = load_multiple_centerlines(
        files
    )


    summarize_centerlines(
        roads
    )

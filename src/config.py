"""
DMV Bus Stops Intelligence Platform
Configuration settings

Central location for:
- API configuration
- database settings
- scoring weights
- project constants

Keep secrets out of GitHub.
Use environment variables for keys/passwords.
"""

import os


# ------------------------------------------------------------
# Project metadata
# ------------------------------------------------------------

PROJECT_NAME = "DMV Bus Stops"

AGENCY = "WMATA"


# ------------------------------------------------------------
# Database configuration
#
# Example:
# export DATABASE_URL="postgresql://user:password@localhost/busstops"
# ------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost/busstops"
)


# ------------------------------------------------------------
# Google Street View configuration
#
# Do NOT hardcode keys here.
# Store with:
#
# export GOOGLE_STREETVIEW_API_KEY="your_key"
# ------------------------------------------------------------

GOOGLE_STREETVIEW_API_KEY = os.getenv(
    "GOOGLE_STREETVIEW_API_KEY"
)


# ------------------------------------------------------------
# File locations
# ------------------------------------------------------------

DATA_DIR = "data"

RAW_DATA_DIR = f"{DATA_DIR}/raw"

PROCESSED_DATA_DIR = f"{DATA_DIR}/processed"


BUS_STOP_FILE = (
    f"{RAW_DATA_DIR}/bus_stops.geojson"
)


RIDERSHIP_FILE = (
    f"{RAW_DATA_DIR}/ridership.csv"
)


CENTERLINE_DIR = (
    f"{RAW_DATA_DIR}/road_centerlines"
)


MANIFEST_DIR = (
    f"{PROCESSED_DATA_DIR}/manifests"
)



# ------------------------------------------------------------
# Street View settings
# ------------------------------------------------------------

STREETVIEW_IMAGE_SIZE = "640x640"

STREETVIEW_FOV = 90

STREETVIEW_PITCH = 0


# Two images per stop:
#
# image 1:
# primary view toward stop
#
# image 2:
# slightly rotated view
#
# Useful because shelters/benches can be hidden
# by the first camera angle.

SECOND_IMAGE_OFFSET_DEGREES = 15



# ------------------------------------------------------------
# Spatial matching settings
# ------------------------------------------------------------

# Maximum distance allowed between stop
# and road centerline.

MAX_CENTERLINE_DISTANCE_METERS = 60


# Number of road segments checked before
# calculating exact nearest geometry.

K_NEAREST_ROADS = 8



# Maximum distance for matching OSM objects
# like benches/shelters.

MAX_OSM_MATCH_DISTANCE_METERS = 30



# ------------------------------------------------------------
# Bench opportunity scoring weights
#
# These are initial placeholders.
# Later we will tune them using real results.
# ------------------------------------------------------------

SCORING_WEIGHTS = {

    # demand from WMATA ridership
    "ridership": 0.30,


    # stop lacks existing shelter/bench
    "amenity_gap": 0.20,


    # physical ability to install bench
    "feasibility": 0.25,


    # people requesting improvement
    "community_demand": 0.15,


    # equity/community priority factors
    "equity": 0.10

}



# ------------------------------------------------------------
# Volunteer review settings
# ------------------------------------------------------------

DEFAULT_REVIEW_BATCH_SIZE = 500


# Priority multiplier:
#
# Higher means the system favors stops
# with greater uncertainty or importance.

HIGH_PRIORITY_MULTIPLIER = 2.0



# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO"
)

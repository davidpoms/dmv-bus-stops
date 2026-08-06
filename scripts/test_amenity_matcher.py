from src.amenities.matcher import find_nearest_physical_stop

DB = "src/database/dmv_bus_stops.db"


result = find_nearest_physical_stop(
    DB,
    38.904067,
    -77.046757
)

print(result)
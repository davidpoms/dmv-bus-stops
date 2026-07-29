from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = r'''

def osm_amenity_metrics():

    return query(
        """
        SELECT

            (
                SELECT COUNT(*)
                FROM physical_stops p

                WHERE EXISTS (

                    SELECT 1
                    FROM osm_features o

                    WHERE o.tags LIKE '%"highway": "bus_stop"%'
                    AND o.tags LIKE '%"bench": "yes"%'

                    AND (
                        (p.latitude-o.lat)*(p.latitude-o.lat)
                        +
                        (p.longitude-o.lon)*(p.longitude-o.lon)
                    ) < 0.0000005

                )

            ) AS osm_bench_stops,


            (
                SELECT COUNT(*)
                FROM physical_stops p

                WHERE EXISTS (

                    SELECT 1
                    FROM osm_features o

                    WHERE o.tags LIKE '%"highway": "bus_stop"%'
                    AND o.tags LIKE '%"shelter": "yes"%'

                    AND (
                        (p.latitude-o.lat)*(p.latitude-o.lat)
                        +
                        (p.longitude-o.lon)*(p.longitude-o.lon)
                    ) < 0.0000005

                )

            ) AS osm_shelter_stops

        """
    )[0]

'''

if "def osm_amenity_metrics" not in text:
    text += addition
    print("Added OSM amenity metrics")
else:
    print("Already exists")

p.write_text(text)

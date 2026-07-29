from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''
                    "assigned":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_review_assignments
                        WHERE stop_id IN ({})
                        """),
'''

new = '''
                    "review": {

                        "needs_review":
                            count("""
                            SELECT COUNT(*)
                            FROM review_queue
                            WHERE physical_stop_id IN ({})
                            """),

                        "completed":
                            count("""
                            SELECT COUNT(DISTINCT physical_stop_id)
                            FROM stop_observations
                            WHERE physical_stop_id IN ({})
                            """),
                    },


                    "osm": {

                        "mapped_benches":
                            count("""
                            SELECT COUNT(*)
                            FROM stop_osm_evidence
                            WHERE stop_id IN ({})
                            AND osm_bench = 1
                            """),

                        "mapped_shelters":
                            count("""
                            SELECT COUNT(*)
                            FROM stop_osm_evidence
                            WHERE stop_id IN ({})
                            AND osm_shelter = 1
                            """),
                    },


                    "confirmed_conditions": {

                        "benches":
                            count("""
                            SELECT COUNT(*)
                            FROM stop_consensus
                            WHERE stop_id IN ({})
                            AND has_bench = 1
                            """),

                        "shelters":
                            count("""
                            SELECT COUNT(*)
                            FROM stop_consensus
                            WHERE stop_id IN ({})
                            AND has_shelter = 1
                            """),

                        "bench_space":
                            count("""
                            SELECT COUNT(*)
                            FROM stop_consensus
                            WHERE stop_id IN ({})
                            AND bench_feasible = 1
                            """),
                    },
'''

if old not in text:
    raise SystemExit("Could not find old block")

text = text.replace(old, new)

# remove old fields from the response
text = text.replace('''
                    "assigned":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_review_assignments
                        WHERE stop_id IN ({})
                        """),
''','')

text = text.replace('''
                    "bench_confirmed":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_consensus
                        WHERE stop_id IN ({})
                        AND has_bench=1
                        """),
''','')

p.write_text(text)

print("Pipeline labels updated")

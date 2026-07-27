from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''
                    "bench_confirmed":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_consensus
                        WHERE stop_id IN ({})
                        AND has_bench=1
                        """)

                }
'''

new = '''
                    "bench_confirmed":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_consensus
                        WHERE stop_id IN ({})
                        AND has_bench=1
                        """),

                    "completion_pct":
                        round(
                            (
                                count("""
                                SELECT COUNT(*)
                                FROM stop_observations
                                WHERE physical_stop_id IN ({})
                                """)
                                +
                                count("""
                                SELECT COUNT(*)
                                FROM stop_consensus
                                WHERE stop_id IN ({})
                                """)
                            )
                            /
                            len(stops)
                            *
                            100,
                            1
                        )

                }
'''

if old not in text:
    raise Exception("Could not find insertion point")

text = text.replace(old,new)

p.write_text(text)

print("Added pipeline completion percentage")

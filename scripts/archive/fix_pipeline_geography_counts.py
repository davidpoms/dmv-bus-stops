from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

start = text.index('@app.route("/pipeline/geography")')
end = text.index('if __name__ == "__main__":')

new_route = r'''
@app.route("/pipeline/geography")
def pipeline_geography():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()


    rows = []


    geographies = [

        (
            "DC Ward",
            """
            SELECT
                dc_ward as geography,
                stop_id
            FROM stop_jurisdiction
            WHERE dc_ward IS NOT NULL
            """
        ),

        (
            "ANC",
            """
            SELECT
                dc_anc as geography,
                stop_id
            FROM stop_jurisdiction
            WHERE dc_anc IS NOT NULL
            """
        ),

        (
            "County",
            """
            SELECT
                state || ' - ' || county as geography,
                stop_id
            FROM stop_jurisdiction
            WHERE county IS NOT NULL
            """
        ),

        (
            "Municipality",
            """
            SELECT
                state || ' - ' || municipality as geography,
                stop_id
            FROM stop_jurisdiction
            WHERE municipality IS NOT NULL
            """
        )

    ]


    for geo_type, query in geographies:

        cur.execute(query)

        groups = {}

        for r in cur.fetchall():

            groups.setdefault(
                r["geography"],
                []
            ).append(
                r["stop_id"]
            )


        for name, stops in groups.items():

            placeholders = ",".join(
                ["?"] * len(stops)
            )


            def count(sql):
                cur.execute(
                    sql.format(placeholders),
                    stops
                )
                return cur.fetchone()[0]


            rows.append(
                {

                    "type": geo_type,

                    "geography": name,

                    "stops": len(stops),

                    "queued":
                        count("""
                        SELECT COUNT(*)
                        FROM review_queue
                        WHERE physical_stop_id IN ({})
                        """),

                    "assigned":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_review_assignments
                        WHERE stop_id IN ({})
                        """),

                    "reviewed":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_observations
                        WHERE physical_stop_id IN ({})
                        """),

                    "consensus":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_consensus
                        WHERE stop_id IN ({})
                        AND consensus_status='verified'
                        """),

                    "bench_confirmed":
                        count("""
                        SELECT COUNT(*)
                        FROM stop_consensus
                        WHERE stop_id IN ({})
                        AND has_bench=1
                        """)

                }
            )


    conn.close()

    return jsonify(rows)

'''


text = text[:start] + new_route + "\n\n" + text[end:]

p.write_text(text)

print("Pipeline counts now geography-specific")

from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

route = r'''

@app.route("/pipeline/geography")
def pipeline_geography():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()


    geography_rows = []


    # ---- DC Wards ----

    cur.execute("""
    SELECT
        'DC Ward' as type,
        dc_ward as geography,
        COUNT(*) as stops
    FROM stop_jurisdiction
    WHERE dc_ward IS NOT NULL
    GROUP BY dc_ward
    """)

    geography_rows.extend(
        dict(r)
        for r in cur.fetchall()
    )


    # ---- ANC ----

    cur.execute("""
    SELECT
        'ANC' as type,
        dc_anc as geography,
        COUNT(*) as stops
    FROM stop_jurisdiction
    WHERE dc_anc IS NOT NULL
    GROUP BY dc_anc
    """)

    geography_rows.extend(
        dict(r)
        for r in cur.fetchall()
    )


    # ---- Counties ----

    cur.execute("""
    SELECT
        'County' as type,
        state || ' - ' || county as geography,
        COUNT(*) as stops
    FROM stop_jurisdiction
    WHERE county IS NOT NULL
    GROUP BY state, county
    """)

    geography_rows.extend(
        dict(r)
        for r in cur.fetchall()
    )


    # ---- Municipalities ----

    cur.execute("""
    SELECT
        'Municipality' as type,
        state || ' - ' || municipality as geography,
        COUNT(*) as stops
    FROM stop_jurisdiction
    WHERE municipality IS NOT NULL
    GROUP BY state, municipality
    """)

    geography_rows.extend(
        dict(r)
        for r in cur.fetchall()
    )


    # ---- Pipeline counts ----

    for row in geography_rows:

        # temporarily global counts;
        # next pass will make these geography-specific joins

        cur.execute(
            "SELECT COUNT(*) FROM review_queue"
        )
        row["identified"] = cur.fetchone()[0]


        cur.execute(
            "SELECT COUNT(*) FROM stop_review_assignments"
        )
        row["assigned"] = cur.fetchone()[0]


        cur.execute(
            "SELECT COUNT(*) FROM stop_observations"
        )
        row["reviewed"] = cur.fetchone()[0]


        cur.execute("""
        SELECT COUNT(*)
        FROM stop_consensus
        WHERE consensus_status='verified'
        """)
        row["consensus"] = cur.fetchone()[0]


        cur.execute("""
        SELECT COUNT(*)
        FROM stop_consensus
        WHERE has_bench=1
        """)
        row["bench_confirmed"] = cur.fetchone()[0]


    conn.close()

    return jsonify(geography_rows)

'''

# insert BEFORE the main runner
marker = "if __name__ == \"__main__\":"

if "/pipeline/geography" not in text:

    text = text.replace(
        marker,
        route + "\n\n" + marker
    )

    p.write_text(text)

print("Pipeline geography route added")

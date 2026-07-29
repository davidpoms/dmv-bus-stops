from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

marker = """
@app.route("/api/status")
"""

if marker not in text:
    raise SystemExit("API insertion point not found")


route = r'''

@app.route("/api/evidence-summary")
def evidence_summary():

    summary = query_db(
        """
        SELECT

        COUNT(*) AS total,

        SUM(
            CASE
            WHEN
                COALESCE(w.wmata_shelter,'') != ''
                OR COALESCE(o.osm_shelter,0)=1
            THEN 1 ELSE 0
            END
        ) AS likely_shelter,

        SUM(
            CASE
            WHEN
                COALESCE(w.wmata_bench,'') != ''
                OR COALESCE(o.osm_bench,0)=1
            THEN 1 ELSE 0
            END
        ) AS likely_bench,

        SUM(
            CASE
            WHEN
                COALESCE(w.wmata_shelter,'')=''
                AND COALESCE(o.osm_shelter,0)=0
            THEN 1 ELSE 0
            END
        ) AS no_shelter_evidence

        FROM physical_stops p

        LEFT JOIN stop_wmata_evidence w
        ON p.id=w.physical_stop_id

        LEFT JOIN stop_osm_evidence o
        ON p.id=o.stop_id

        """
    )[0]


    return {
        "total": summary["total"],
        "likely_shelter": summary["likely_shelter"],
        "likely_bench": summary["likely_bench"],
        "no_shelter_evidence": summary["no_shelter_evidence"]
    }

'''

text=text.replace(
    marker,
    route + "\n" + marker
)

path.write_text(text)

print("Added evidence summary API")

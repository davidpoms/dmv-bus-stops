"""
DMV Bus Stops Improvement API
"""

from flask import Flask, jsonify
import sqlite3
from pathlib import Path


app = Flask(__name__)


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    /
    "src"
    /
    "database"
    /
    "dmv_bus_stops.db"
)


def query_db(sql, params=()):

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()

    cursor.execute(
        sql,
        params
    )

    rows = cursor.fetchall()

    conn.close()

    return rows



@app.route("/")
def home():

    return jsonify(
        {
            "name": "DMV Bus Stop Improvement API",
            "status": "running",
            "endpoints": [
                "/summary",
                "/projects",
                "/stops/<stop_id>"
            ]
        }
    )



@app.route("/projects")
def projects():

    rows = query_db(
        """
        SELECT

            ip.physical_stop_id,

            ps.primary_name,

            ip.recommendation_type,

            ip.project_status,

            io.opportunity_score

        FROM improvement_projects ip

        JOIN physical_stops ps

            ON ip.physical_stop_id = ps.id

        JOIN improvement_opportunities io

            ON ip.physical_stop_id =
               io.physical_stop_id

        ORDER BY
            io.opportunity_score DESC;
        """
    )


    return jsonify(
        [
            {
                "stop_id": row[0],
                "location": row[1],
                "recommendation": row[2],
                "status": row[3],
                "score": row[4]
            }
            for row in rows
        ]
    )



@app.route("/stops/<int:stop_id>")
def stop_detail(stop_id):

    stop = query_db(
        """
        SELECT

            ps.primary_name,

            sii.opportunity_score,

            sii.impact_level

        FROM physical_stops ps

        JOIN stop_improvement_impact sii

            ON ps.id = sii.physical_stop_id

        WHERE ps.id = ?;
        """,
        (stop_id,)
    )


    projects = query_db(
        """
        SELECT

            recommendation_type,

            project_status

        FROM improvement_projects

        WHERE physical_stop_id = ?;
        """,
        (stop_id,)
    )


    return jsonify(
        {
            "stop": stop[0] if stop else None,

            "projects": [
                {
                    "recommendation": row[0],
                    "status": row[1]
                }
                for row in projects
            ]
        }
    )



@app.route("/summary")
def summary():

    return jsonify(
        {
            "message":
                "Summary endpoint ready"
        }
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

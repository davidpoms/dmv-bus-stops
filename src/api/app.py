import json

"""
DMV Bus Stops Improvement API
"""

from flask import Flask, jsonify, send_from_directory, request, render_template
import sqlite3
from pathlib import Path

from src.assessment.interpretation import (
    summarize_stop_evidence,
    generate_review_action_summary,
    interpret_bench_status,
    interpret_review_priority,
)


app = Flask(
    __name__,
    static_folder=None,
    template_folder="../dashboard/templates"
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


def query_db(sql, params=()):

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    cursor.execute(sql, params)

    conn.commit()

    rows = cursor.fetchall()

    conn.close()

    return rows






def get_stop_evidence_summary(stop_id):

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    transit = conn.execute(
        """
        SELECT *
        FROM stop_transit_evidence
        WHERE stop_id=?
        """,
        (stop_id,)
    ).fetchone()


    osm = conn.execute(
        """
        SELECT *
        FROM stop_osm_evidence
        WHERE stop_id=?
        """,
        (stop_id,)
    ).fetchone()


    reviews = conn.execute(
        """
        SELECT *
        FROM stop_observations
        WHERE physical_stop_id=?
        ORDER BY observed_at DESC
        """,
        (stop_id,)
    ).fetchall()


    conn.close()


    return {
        "transit": dict(transit) if transit else None,

        "osm": dict(osm) if osm else None,

        "reviews": [
            dict(r)
            for r in reviews
        ]
    }


@app.route("/observations/create", methods=["POST"])
def create_observation():

    data = request.json

    conn = sqlite3.connect(DATABASE_PATH)

    conn.execute(
        """
        INSERT INTO stop_observations
        (
            physical_stop_id,
            observer,
            shelter_present,
            bench_present,
            trash_present,
            bench_feasible,
            ada_clearance_possible,
            review_mode,
            reviewer_relationship,
            rider_activity,
            usage_times,
            property_owner_outreach,
            steward_email,
            steward_candidate,
            notes
        )
        
VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """,
        (
            data["stop_id"],
            data.get("observer", ""),
            data.get("shelter_present"),
            data.get("bench_present"),
            data.get("trash_present"),
            data.get("bench_feasible"),
            data.get("ada_clearance_possible"),
            data.get("review_mode"),
            data.get("rider_activity"),
            data.get("usage_times"),
            data.get("property_owner_outreach"),
            data.get("steward_email"),
            data.get("steward_candidate", 0),
            data.get("notes", "")
        )
    )

    conn.commit()
    conn.close()

    return jsonify(
        {
            "success": True,
            "stop_id": data["stop_id"]
        }
    )


@app.route("/validation/update", methods=["POST"])
def validation_update():

    data = request.json

    stop_id = data["stop_id"]
    status = data["status"]
    validator = data.get("validator", "")
    notes = data.get("notes", "")


    conn = sqlite3.connect(
        "src/database/dmv_bus_stops.db"
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        INSERT INTO stop_validation
        (
            physical_stop_id,
            status,
            validator,
            notes,
            validated_at
        )

        VALUES (?, ?, ?, ?, datetime('now'))

        ON CONFLICT(physical_stop_id)
        DO UPDATE SET

            status = excluded.status,
            validator = excluded.validator,
            notes = excluded.notes,
            validated_at = excluded.validated_at
        """,
        (
            stop_id,
            status,
            validator,
            notes
        )
    )


    conn.commit()
    conn.close()


    return jsonify(
        {
            "success": True,
            "stop_id": stop_id,
            "status": status
        }
    )


@app.route("/validation/queue")
def validation_queue():

    rows = query_db(
        '''
        SELECT
            ps.id,
            ps.primary_name,
            ps.latitude AS lat,
            ps.longitude AS lon,
            sii.opportunity_score,
            sii.priority_level,
            sv.status

        FROM stop_validation sv

        JOIN stop_improvement_impact sii
            ON sv.physical_stop_id = sii.physical_stop_id

        JOIN physical_stops ps
            ON ps.id = sv.physical_stop_id

        WHERE sv.status = 'needs_validation'

        ORDER BY
            CASE sii.priority_level
                WHEN 'P1' THEN 1
                WHEN 'P2' THEN 2
                WHEN 'P3' THEN 3
                ELSE 4
            END,
            sii.opportunity_score DESC

        LIMIT 75;
        '''
    )

    return jsonify(
        [
            {
                "stop_id": row[0],
                "location": row[1],
                "lat": row[2],
                "lon": row[3],
                "score": row[4],
                "priority": row[5],
                "status": row[6],
                "streetview_url":
                    f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
            }

            for row in rows
        ]
    )



@app.route("/")
def home():

    return send_from_directory(
        BASE_DIR,
        "dmv_bus_stops_dashboard.html"
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
            ON ip.physical_stop_id = io.physical_stop_id

        ORDER BY io.opportunity_score DESC;
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



@app.route("/stops/<int:stop_id>/community-status")
def community_status(stop_id):

    validation = query_db(
        """
        SELECT
            status,
            validator,
            validated_at
        FROM stop_validation
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )


    review_count = query_db(
        """
        SELECT COUNT(*)
        FROM stop_observations
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )[0][0]


    observation_count = query_db(
        """
        SELECT COUNT(*)
        FROM stop_observations
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )[0][0]


    projects = query_db(
        """
        SELECT
            recommendation_type,
            project_status,
            assigned_team,
            completed_date
        FROM improvement_projects
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )


    community_actions = query_db(
        """
        SELECT
            status,
            project_type,
            steward,
            installed_date,
            notes
        FROM community_actions
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )


    if validation:

        validation_status = validation[0][0]
        validator = validation[0][1]
        validated_at = validation[0][2]

    else:

        validation_status = "needs_validation"
        validator = None
        validated_at = None



    installed_projects = []

    for project in projects:

        installed_projects.append(
            {
                "type": project[0],
                "status": project[1],
                "steward": project[2],
                "completed_date": project[3]
            }
        )


    required_reviews = 3


    streetview_status = (
        "consensus_reached"
        if review_count >= required_reviews
        else
        "awaiting_consensus"
    )


    field_review_status = (
        "completed"
        if validation_status == "validated"
        else
        "not_started"
    )


    current_action = (
        community_actions[0]
        if community_actions
        else None
    )


    return jsonify(
        {
            "journey": {

                "opportunity_identified": True,


                "streetview": {

                    "required_reviews":
                        required_reviews,

                    "completed_reviews":
                        review_count,

                    "status":
                        streetview_status
                },


                "field_review": {

                    "status":
                        field_review_status,

                    "validator":
                        validator,

                    "validated_at":
                        validated_at
                },


                "community_project": {

                    "status":
                        "active"
                        if installed_projects
                        else
                        "none",

                    "improvements":
                        installed_projects
                },


                "community_action": [

                    {
                        "status": row[0],
                        "type": row[1],
                        "steward": row[2],
                        "installed_date": row[3],
                        "notes": row[4]
                    }

                    for row in community_actions
                ],


                "current_action":
                    {
                        "status": current_action[0],
                        "type": current_action[1],
                        "steward": current_action[2],
                        "installed_date": current_action[3],
                        "notes": current_action[4]
                    }
                    if current_action
                    else None

            }
        }
    )



@app.route("/stops/<int:stop_id>")
def stop_detail(stop_id):

    stop = query_db(
        """
        SELECT
            ps.primary_name,
            ps.latitude AS lat,
            ps.longitude AS lon,
            sii.opportunity_score,
            sii.priority_level

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


    recommendations = query_db(
        """
        SELECT
            recommendation_type,
            priority,
            confidence,
            evidence,
            reasons

        FROM improvement_recommendations

        WHERE physical_stop_id = ?

        ORDER BY
            priority,
            recommendation_type;
        """,
        (stop_id,)
    )


    recommendation_payload = []

    for row in recommendations:

        recommendation_payload.append(
            {
                "type": row[0],
                "priority": row[1],
                "confidence": row[2],
                "evidence": json.loads(row[3]) if row[3] else {},
                "reasons": json.loads(row[4]) if row[4] else []
            }
        )


    stop_row = stop[0] if stop else None

    evidence = get_stop_evidence_summary(stop_id)

    bench_status = interpret_bench_status(evidence)

    review_priority = interpret_review_priority(
        evidence,
        bench_status
    )

    evidence_summary = summarize_stop_evidence(
        evidence
    )

    review_actions = generate_review_action_summary(
        evidence,
        review_priority
    )


    return jsonify(
        {
            "stop":
                {
                    "location": stop_row[0],
                    "lat": stop_row[1],
                    "lon": stop_row[2],
                    "score": stop_row[3],
                    "impact": stop_row[4]
                }
                if stop_row else None,

            "projects": [
                {
                    "recommendation": row[0],
                    "status": row[1]
                }
                for row in projects
            ],

            "recommendations": recommendation_payload,

            "evidence": evidence,

            "evidence_summary": evidence_summary,

            "review_actions": review_actions,

            "bench_status": bench_status,

            "review_priority": review_priority
        }
    )






@app.route("/survey-page/<int:stop_id>")
def survey_page(stop_id):

    from flask import render_template

    return render_template(
        "survey.html"
    )

@app.route("/survey/<int:stop_id>")
def survey(stop_id):

    stop = query_db(
        """
        SELECT
            ps.id,
            ps.primary_name,
            ps.latitude AS lat,
            ps.longitude

        FROM physical_stops ps

        WHERE ps.id = ?;
        """,
        (stop_id,)
    )

    if not stop:
        return "Stop not found", 404

    row = stop[0]

    return jsonify(
        {
            "stop_id": row[0],
            "location": row[1],
            "lat": row[2],
            "lon": row[3],
            "streetview_url":
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
        }
    )









@app.route("/review/<int:stop_id>")
def review_page(stop_id):

    from src.review.render_survey import render_survey

    stop = query_db(
        """
        SELECT
            id,
            primary_name,
            latitude,
            longitude,
            jurisdiction
        FROM physical_stops
        WHERE id=?
        """,
        (stop_id,)
    )

    if not stop:
        return "Stop not found", 404

    stop_row = list(stop[0])

    # Fallback jurisdiction from coordinates
    if not stop_row[4]:
        lon = stop_row[3]

        if lon < -77.05:
            stop_row[4] = "Virginia"
        elif lon > -76.95:
            stop_row[4] = "Maryland"
        else:
            stop_row[4] = "District of Columbia"

    return render_template(
        "review.html",
        stop=stop_row,
        stop_id=stop_id,
        survey_html=render_survey()
    )



@app.route("/review/<int:stop_id>/info")
def review_stop_info(stop_id):

    stop = query_db(
        """
        SELECT
            id,
            primary_name,
            latitude,
            longitude,
            state,
            dc_ward,
            dc_anc,
            county,
            municipality
        FROM physical_stops
        WHERE id=?
        """,
        (stop_id,)
    )

    if not stop:
        return {"error": "Stop not found"}, 404

    row = stop[0]

    return jsonify(
        {
            "stop_id": row[0],
            "name": row[1],
            "lat": row[2],
            "lon": row[3],
            "state": row[4],
            "ward": row[5],
            "anc": row[6],
            "county": row[7],
            "municipality": row[8],
            "streetview_url":
                f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
        }
    )



@app.route("/review/<int:stop_id>/assignment")
def review_assignment(stop_id):

    assignment = query_db(
        """
        SELECT
            id,
            reviewer_id,
            stop_id

        FROM stop_review_assignments

        WHERE stop_id=?

        ORDER BY id

        LIMIT 1
        """,
        (
            stop_id,
        )
    )

    if not assignment:

        return jsonify(
            {
                "error":
                    "No active assignment found"
            }
        ), 404


    return jsonify(
        {
            "assignment_id":
                assignment[0][0],

            "reviewer_id":
                assignment[0][1],

            "stop_id":
                assignment[0][2]
        }
    )


@app.route("/review/submit", methods=["POST"])
def submit_review():

    data = request.json


    data["shelter_type"] = (
        data.get("shelter_type")
        or data.get("shelter_protection")
        or ""
    )

    data["bench_type"] = (
        data.get("bench_type")
        or data.get("seating_type")
        or ""
    )

    data["bench_condition"] = (
        data.get("bench_condition")
        or data.get("seating_limitations")
        or ""
    )

    data["rider_comfort_category"] = (
        data.get("rider_comfort_category")
        or data.get("waiting_environment_rating")
        or ""
    )

    data["property_owner_outreach"] = data.get(
        "steward_interest",
        ""
    )

    data["steward_candidate"] = (
        1
        if data.get("steward_interest") in ("yes", "maybe")
        else 0
    )


    stop_id = data.get("stop_id")
    reviewer_id = data.get("reviewer_id")
    assignment_id = data.get("assignment_id")


    if not assignment_id or not reviewer_id:
        return {
            "error": "assignment_id and reviewer_id required"
        }, 400


    query_db(
        """
        INSERT INTO stop_observations
        (
            physical_stop_id,
            observer,
            shelter_present,
            bench_present,
            trash_present,
            bench_feasible,
            ada_clearance_possible,
            bench_type,
            bench_condition,
            shelter_type,
            rider_comfort_category,
            accessibility_status,
            notes,
            reviewer_id,
            confidence,
            source,
            review_mode,
            reviewer_relationship,
            rider_activity,
            usage_times,
            property_owner_outreach,
            steward_email,
            steward_candidate,
            concrete_pad_needed
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """,
        (
            stop_id,
            data.get("observer", ""),
            data.get("shelter_present"),
            "yes" if data.get("bench_type") else data.get("bench_present"),
            data.get("trash_present"),
            data.get("bench_feasible"),
            data.get("accessibility_status"),
            data.get("bench_type", ""),
            data.get("bench_condition", ""),
            data.get("shelter_type", ""),
            data.get("rider_comfort_category", ""),
            data.get("accessibility_status"),
            data.get("notes"),
            reviewer_id,
            data.get("reviewer_confidence", "unknown"),
            "community_review",
            data.get("review_mode"),
            data.get("reviewer_relationship"),
            data.get("rider_activity"),
            data.get("usage_times"),
            data.get("property_owner_outreach", ""),
            data.get("steward_email"),
            data.get("steward_candidate", 0),
            data.get("concrete_pad_needed")
        )
    )


    query_db(
        """
        UPDATE stop_review_assignments
        SET status='completed',
            completed_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (assignment_id,)
    )


    return {
        "success": True,
        "stop_id": stop_id
    }


@app.route("/api/review-queue")
def review_queue():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            ir.physical_stop_id,
            ps.latitude AS lat,
            ps.longitude AS lon,
            ir.recommendation_type,
            ir.priority,
            ir.confidence,
            ir.reasons,
            ir.evidence

        FROM improvement_recommendations ir

        JOIN physical_stops ps
            ON ps.id = ir.physical_stop_id

        ORDER BY
            CASE ir.priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                ELSE 3
            END,
            ir.physical_stop_id

        """
    ).fetchall()

    conn.close()

    return jsonify(
        {
            "count": len(rows),
            "queue": [
                {
                    "stop_id": row["physical_stop_id"],
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "type": row["recommendation_type"],
                    "priority": row["priority"],
                    "confidence": row["confidence"],
                    "reasons": json.loads(row["reasons"])
                        if row["reasons"]
                        else [],
                    "evidence": json.loads(row["evidence"])
                        if row["evidence"]
                        else {}
                }
                for row in rows
            ]
        }
    )


@app.route("/stops/<int:stop_id>/review-summary")
def stop_review_summary(stop_id):

    evidence = get_stop_evidence_summary(stop_id)

    transit = evidence.get("transit") or {}
    osm = evidence.get("osm") or {}
    reviews = evidence.get("reviews") or []

    reasons = []

    if transit.get("gtfs_bus_stop"):
        reasons.append(
            "Active transit stop confirmed"
        )

    if not osm.get("osm_bench"):
        reasons.append(
            "No public data evidence of bench"
        )

    if not osm.get("osm_shelter"):
        reasons.append(
            "No public data evidence of shelter"
        )

    if len(reviews) == 0:
        reasons.append(
            "No community observations"
        )


    return jsonify(
        {
            "stop_id": stop_id,

            "review_status": {
                "needs_field_review": len(reasons) > 0,
                "reasons": reasons
            },

            "evidence": {
                "gtfs_confirmed":
                    bool(transit.get("gtfs_bus_stop")),

                "osm_bench":
                    bool(osm.get("osm_bench")),

                "osm_shelter":
                    bool(osm.get("osm_shelter")),

                "community_reviews":
                    len(reviews)
            },

            "recommended_actions": [
                "Verify bench presence",
                "Verify shelter presence",
                "Collect first community observation"
            ]
        }
    )

@app.route("/priorities/top")
def top_priorities():

    rows = query_db(
        """
        SELECT
            ps.primary_name,
            ps.latitude AS lat,
            ps.longitude AS lon,
            sii.opportunity_score,
            sii.priority_level,
            sii.priority_level

        FROM stop_improvement_impact sii

        JOIN physical_stops ps
            ON sii.physical_stop_id = ps.id

        ORDER BY sii.opportunity_score DESC

        LIMIT 10;
        """
    )

    return jsonify(
        [
            {
                "location": row[0],
                "lat": row[1],
                "lon": row[2],
                "score": row[3],
                "priority": row[4],
                "impact": row[5]
            }
            for row in rows
        ]
    )



@app.route("/geography/states")
def geography_states():

    rows = query_db("""
        SELECT DISTINCT state
        FROM stop_jurisdiction
        ORDER BY state
    """)

    return jsonify(
        [row[0] for row in rows]
    )


@app.route("/geography/counties")
def geography_counties():

    state = request.args.get("state")

    rows = query_db(
        """
        SELECT DISTINCT county
        FROM stop_jurisdiction
        WHERE (? IS NULL OR state = ?)
        AND county IS NOT NULL
        ORDER BY county
        """,
        (
            state,
            state
        )
    )

    return jsonify(
        [row[0] for row in rows]
    )


@app.route("/geography/municipalities")
def geography_municipalities():

    county = request.args.get("county")

    rows = query_db(
        """
        SELECT DISTINCT municipality
        FROM stop_jurisdiction
        WHERE (? IS NULL OR county = ?)
        AND municipality IS NOT NULL
        ORDER BY municipality
        """,
        (
            county,
            county
        )
    )

    return jsonify(
        [row[0] for row in rows]
    )


@app.route("/geography/dc-wards")
def geography_dc_wards():

    rows = query_db("""
        SELECT DISTINCT dc_ward
        FROM stop_jurisdiction
        WHERE dc_ward IS NOT NULL
        ORDER BY dc_ward
    """)

    return jsonify(
        [row[0] for row in rows]
    )


@app.route("/map/stops")
def map_stops():

    route = request.args.get("route")

    impact = request.args.get("impact")

    priority = request.args.get("priority")

    state = request.args.get("state")
    county = request.args.get("county")
    municipality = request.args.get("municipality")
    dc_ward = request.args.get("dc_ward")

    review_mode = request.args.get("review")
    action_filter = request.args.get("action")


    if route:

        rows = query_db(
            """
            SELECT DISTINCT

                ps.id,
                ps.primary_name,
                ps.latitude AS lat,
                ps.longitude AS lon,
                sii.opportunity_score,
                sii.priority_level,
                sii.priority_level,
                COALESCE(
                    sv.status,
                    'needs_validation'
                ),

                COALESCE(
                    ca.status,
                    'none'
                )

            FROM physical_stops ps

            JOIN stop_improvement_impact sii
                ON ps.id = sii.physical_stop_id

            LEFT JOIN stop_validation sv
                ON ps.id = sv.physical_stop_id

            LEFT JOIN community_actions ca
                ON ps.id = ca.physical_stop_id

            JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            JOIN bus_stops bs
                ON psm.bus_stop_id = bs.id

            JOIN stop_routes sr
                ON bs.gtfs_stop_id = sr.stop_id

            LEFT JOIN stop_jurisdiction sj
                ON ps.id = sj.stop_id

            WHERE sr.route_id = ?

            AND (
                ? IS NULL
                OR (
                    ? = 'high'
                    AND sii.priority_level IN ('high', 'very_high')
                )
                OR (
                    ? = 'very_high'
                    AND sii.priority_level = 'very_high'
                )
            )

            AND (
                ? IS NULL
                OR sii.priority_level = ?
            )

            AND (
                ? IS NULL
                OR sj.state = ?
            )

            AND (
                ? IS NULL
                OR sj.county = ?
            )

            AND (
                ? IS NULL
                OR sj.municipality = ?
            )

            AND (
                ? IS NULL
                OR sj.dc_ward = ?
            )

            AND (
                ? IS NULL

                OR (
                    ? = 'opportunity'
                    AND (
                        sv.status IS NULL
                        OR sv.status = 'needs_validation'
                    )
                )

                OR (
                    ? = 'candidate'
                    AND sv.status = 'validated'
                )
            )

            AND (
                ? IS NULL
                OR COALESCE(ca.status, 'none') = ?
            )

            ORDER BY sii.opportunity_score DESC;
            """,
            (
                route,
                impact,
                impact,
                impact,
                priority,
                priority,
                state,
                state,
                county,
                county,
                municipality,
                municipality,
                dc_ward,
                dc_ward,
                review_mode,
                review_mode,
                review_mode,
                action_filter,
                action_filter
            )
        )

    else:

        rows = query_db(
            """
            SELECT DISTINCT

                ps.id,
                ps.primary_name,
                ps.latitude AS lat,
                ps.longitude AS lon,
                sii.opportunity_score,
                sii.priority_level,
                sii.priority_level,
                COALESCE(
                    sv.status,
                    'needs_validation'
                ),

                COALESCE(
                    ca.status,
                    'none'
                )

            FROM physical_stops ps

            JOIN stop_improvement_impact sii
                ON ps.id = sii.physical_stop_id

            LEFT JOIN stop_validation sv
                ON ps.id = sv.physical_stop_id

            LEFT JOIN community_actions ca
                ON ps.id = ca.physical_stop_id

            LEFT JOIN stop_jurisdiction sj
                ON ps.id = sj.stop_id

            WHERE (
                ? IS NULL
                OR (
                    ? = 'high'
                    AND sii.priority_level IN ('high', 'very_high')
                )
                OR (
                    ? = 'very_high'
                    AND sii.priority_level = 'very_high'
                )
            )

            AND (
                ? IS NULL
                OR sii.priority_level = ?
            )

            AND (
                ? IS NULL
                OR sj.state = ?
            )

            AND (
                ? IS NULL
                OR sj.county = ?
            )

            AND (
                ? IS NULL
                OR sj.municipality = ?
            )

            AND (
                ? IS NULL
                OR sj.dc_ward = ?
            )

            AND (
                ? IS NULL

                OR (
                    ? = 'opportunity'
                    AND (
                        sv.status IS NULL
                        OR sv.status = 'needs_validation'
                    )
                )

                OR (
                    ? = 'candidate'
                    AND sv.status = 'validated'
                )
            )

            AND (
                ? IS NULL
                OR COALESCE(ca.status, 'none') = ?
            )

            ORDER BY sii.opportunity_score DESC;
            """,
            (
                impact,
                impact,
                impact,
                priority,
                priority,
                state,
                state,
                county,
                county,
                municipality,
                municipality,
                dc_ward,
                dc_ward,
                review_mode,
                review_mode,
                review_mode,
                action_filter,
                action_filter
            )
        )


    return jsonify(
        {
            "type": "FeatureCollection",

            "features": [

                {
                    "type": "Feature",

                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            row[3],
                            row[2]
                        ]
                    },

                    "properties": {
                        "stop_id": row[0],
                        "location": row[1],
                        "score": row[4],
                        "impact": row[5],
                        "priority": row[6],
                        "validation_status": row[7],
                        "action_status": row[8]
                    }
                }

                for row in rows
            ]
        }
    )






@app.route("/stops/<int:stop_id>/community-action", methods=["POST"])
def create_community_action(stop_id):

    data = request.get_json()

    status = data.get(
        "status",
        "planned"
    )

    project_type = data.get(
        "project_type"
    )

    steward = data.get(
        "steward"
    )

    notes = data.get(
        "notes"
    )


    existing_action = query_db(
        """
        SELECT
            id,
            status
        FROM community_actions
        WHERE physical_stop_id = ?
        AND status IN (
            'planned',
            'in_progress',
            'installed'
        )
        ORDER BY id DESC
        LIMIT 1
        """,
        (stop_id,)
    )


    if existing_action:

        existing_id = existing_action[0][0]
        existing_status = existing_action[0][1]

        lifecycle = {
            "planned": 1,
            "in_progress": 2,
            "installed": 3
        }


        if (
            status in lifecycle
            and existing_status in lifecycle
            and lifecycle[status] > lifecycle[existing_status]
        ):

            query_db(
                """
                UPDATE community_actions
                SET
                    status = ?,
                    project_type = ?,
                    steward = ?,
                    installed_date =
                        CASE
                            WHEN ? = 'installed'
                            THEN CURRENT_TIMESTAMP
                            ELSE installed_date
                        END,
                    notes = ?
                WHERE id = ?
                """,
                (
                    status,
                    project_type,
                    steward,
                    status,
                    notes,
                    existing_id
                )
            )


            return jsonify(
                {
                    "status": "updated",
                    "stop_id": stop_id,
                    "previous_status":
                        existing_status,
                    "new_status":
                        status
                }
            )


        return jsonify(
            {
                "status": "already_exists",
                "stop_id": stop_id,
                "existing_status":
                    existing_status
            }
        )


    query_db(
        """
        INSERT INTO community_actions
        (
            physical_stop_id,
            status,
            project_type,
            steward,
            notes
        )
        VALUES
        (?, ?, ?, ?, ?)
        """,
        (
            stop_id,
            status,
            project_type,
            steward,
            notes
        )
    )


    return jsonify(
        {
            "status": "created",
            "stop_id": stop_id
        }
    )



@app.route("/community-actions/summary")
@app.route("/community-action-summary")
def community_action_summary():

    rows = query_db(
        """
        SELECT
            status,
            COUNT(*)
        FROM community_actions
        GROUP BY status
        """
    )


    summary = {
        "planned": 0,
        "in_progress": 0,
        "installed": 0,
        "total": 0
    }


    for row in rows:

        if row[0] in summary:
            summary[row[0]] = row[1]

        summary["total"] += row[1]


    return jsonify(summary)




@app.route("/validation/status-summary")
def validation_status_summary():

    rows = query_db(
        """
        SELECT
            status,
            COUNT(*) AS count
        FROM stop_validation
        GROUP BY status
        ORDER BY count DESC
        """
    )

    return jsonify(
        [
            {
                "status": row[0],
                "count": row[1]
            }
            for row in rows
        ]
    )



@app.route("/priority-summary")
def priority_summary():

    rows = query_db(
        """
        SELECT
            priority_level,
            COUNT(*) AS count

        FROM stop_improvement_impact

        GROUP BY priority_level;
        """
    )

    summary = {
        "P1": 0,
        "P2": 0,
        "P3": 0,
        "monitor": 0
    }

    for row in rows:
        if row[0] in summary:
            summary[row[0]] = row[1]

    return jsonify(summary)



@app.route("/routes")
def routes():

    rows = query_db(
        """
        SELECT

            r.route_id,
            r.route_name,
            COUNT(DISTINCT ps.id)

        FROM routes r

        JOIN stop_routes sr
            ON r.route_id = sr.route_id

        JOIN bus_stops bs
            ON sr.stop_id = bs.gtfs_stop_id

        JOIN physical_stop_members psm
            ON bs.id = psm.bus_stop_id

        JOIN physical_stops ps
            ON psm.physical_stop_id = ps.id

        GROUP BY
            r.route_id,
            r.route_name

        ORDER BY
            r.route_id;
        """
    )


    return jsonify(
        [
            {
                "route_id": row[0],
                "route_name": row[1],
                "stop_count": row[2]
            }

            for row in rows
        ]
    )





@app.route("/static/<path:filename>")
def dashboard_static(filename):

    return send_from_directory(
        BASE_DIR / "src" / "dashboard" / "static",
        filename
    )

@app.route("/dashboard")
def dashboard():

    return send_from_directory(
        BASE_DIR,
        "dmv_bus_stops_dashboard.html"
    )



@app.route("/api/status")
def api_status():

    return jsonify(
        {
            "name": "DMV Bus Stop Improvement API",
            "status": "running"
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
            )


    conn.close()

    return jsonify(rows)



if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )


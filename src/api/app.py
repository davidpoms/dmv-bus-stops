import json

"""
DMV Bus Stops Improvement API
"""

from flask import Flask, jsonify, send_from_directory, request, render_template, redirect, session
import sqlite3
from pathlib import Path


from src.review.assignment_router import (
    get_or_create_reviewer,
    assign_stop,
)

from src.spatial.nearest_road import RoadSpatialIndex

from src.assessment.interpretation import (
    interpret_ddot_evidence,
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

app.secret_key = "dmv-bus-stops-review-secret"

BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)





def get_wmata_history(stop_id):

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            wmata_stop_id,
            wmata_status,
            wmata_heading,
            wmata_bench,
            wmata_shelter,
            wmata_accessible,
            match_distance_m,
            match_confidence,
            created_at

        FROM stop_wmata_evidence

        WHERE physical_stop_id = ?

        ORDER BY
            created_at DESC,
            match_distance_m ASC
        """,
        (stop_id,)
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]




def get_wmata_evidence(stop_id):

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        """
        SELECT
            wmata_stop_id,
            wmata_status,
            wmata_bench,
            wmata_shelter,
            wmata_accessible,
            match_confidence,
            match_distance_m

        FROM stop_wmata_evidence

        WHERE physical_stop_id = ?

        ORDER BY
            CASE
                WHEN wmata_status = 'PRS'
                THEN 0
                ELSE 1
            END,
            match_distance_m ASC

        LIMIT 1
        """,
        (stop_id,)
    ).fetchone()

    conn.close()

    return dict(row) if row else None



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


    ddot = conn.execute(
        """
        SELECT *
        FROM stop_ddot_shelter_evidence
        WHERE physical_stop_id=?
        ORDER BY created_at DESC
        """,
        (stop_id,)
    ).fetchall()


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

        "ddot": [
            dict(r)
            for r in ddot
        ],

        "reviews": [
            dict(r)
            for r in reviews
        ]
    }


road_index = None



def get_road_index():

    global road_index

    if road_index is not None:
        return road_index


    try:

        rows = query_db(
            """
            SELECT geometry, road_class
            FROM road_centerlines
            """
        )


        roads = []

        for row in rows:

            geometry = json.loads(row[0])

            roads.append(
                {
                    "geometry": geometry["coordinates"],
                    "road_class": row[1]
                }
            )


        road_index = RoadSpatialIndex(
            roads
        )


    except Exception as e:

        print("Road centerlines index build failed:", e)


        class EmptyRoadIndex:

            def nearest_road(self, lat, lon):
                return None


        road_index = EmptyRoadIndex()


    return road_index


@app.route("/observations/create", methods=["POST"])
def create_observation():

    data = request.json


    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )




    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )

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

    streetview = get_road_index().nearest_road(
        row[3],
        row[2]
    )


    heading = 0

    if streetview and streetview["heading"] is not None:
        heading = streetview["heading"]


    streetview_url = (
        "https://www.google.com/maps/@?api=1"
        "&map_action=pano"
        f"&viewpoint={road['road_lat']},{road['road_lon']}"
        f"&heading={heading}"
        "&pitch=0"
        "&fov=90"
    )

    reviewer_id = None

    reviewer_key = session.get(
        "reviewer_key"
    )


    if reviewer_key:

        reviewer_id, reviewer_key = get_or_create_reviewer(
            reviewer_key
        )


    reviewer_history = []


    if reviewer_id:

        reviewer_history = query_db(
            """
            SELECT
                id,
                observed_at

            FROM stop_observations

            WHERE physical_stop_id=?

            AND reviewer_id=?

            AND source='community_review'

            ORDER BY observed_at DESC
            """,
            (
                stop_id,
                reviewer_id
            )
        )


    total_reviews = query_db(
        """
        SELECT COUNT(*)

        FROM stop_observations

        WHERE physical_stop_id=?

        AND source='community_review'
        """,
        (stop_id,)
    )


    community_review = {

        "has_reviewed": bool(reviewer_history),

        "review_count":
            len(reviewer_history),

        "total_stop_reviews":
            total_reviews[0][0]
            if total_reviews
            else 0,

        "latest_review_id":
            reviewer_history[0][0]
            if reviewer_history
            else None,

        "last_reviewed_at":
            reviewer_history[0][1]
            if reviewer_history
            else None
    }


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
    confidence = data.get("confidence", "needs_validation")
    notes = data.get("notes", "")

    conn = sqlite3.connect(
        "src/database/dmv_bus_stops.db"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO stop_consensus
        (
            stop_id,
            confidence,
            notes,
            updated_at
        )

        VALUES (?, ?, ?, datetime('now'))

        ON CONFLICT(stop_id)
        DO UPDATE SET

            confidence = excluded.confidence,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """,
        (
            stop_id,
            confidence,
            notes
        )
    )


    conn.commit()
    conn.close()


    return jsonify(
        {
            "success": True,
            "stop_id": stop_id,
            "confidence": confidence
        }
    )

@app.route("/validation/queue")
def validation_queue():

    rows = query_db(
        """
        SELECT
            ps.id,
            ps.primary_name,
            ps.latitude AS lat,
            ps.longitude AS lon,
            io.opportunity_score,

            CASE
                WHEN io.opportunity_score >= 80 THEN 'very_high'
                WHEN io.opportunity_score >= 60 THEN 'high'
                WHEN io.opportunity_score >= 40 THEN 'medium'
                ELSE 'low'
            END,

            COALESCE(
                sc.confidence,
                'needs_validation'
            )

        FROM physical_stops ps

        LEFT JOIN improvement_opportunities io
            ON ps.id = io.physical_stop_id

        LEFT JOIN stop_consensus sc
            ON ps.id = sc.stop_id

        WHERE
            sc.confidence IS NULL
            OR sc.confidence = 'needs_validation'

        ORDER BY
            io.opportunity_score DESC

        LIMIT 75;
        """
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
        FROM stop_consensus
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
        FROM stop_observations
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



@app.route("/stop/<int:stop_id>")
def stop_page(stop_id):

    try:
        return render_template(
            "stop_detail.html",
            stop_id=stop_id
        )

    except Exception as e:
        return f"TEMPLATE ERROR: {type(e).__name__}: {e}", 500



@app.route("/stops/<int:stop_id>")
def stop_detail(stop_id):

    stop = query_db(
"""
SELECT
    ps.primary_name,
    ps.latitude,
    ps.longitude,
    io.opportunity_score,

    CASE
        WHEN io.opportunity_score >= 80 THEN 'very_high'
        WHEN io.opportunity_score >= 60 THEN 'high'
        WHEN io.opportunity_score >= 40 THEN 'medium'
        ELSE 'low'
    END AS impact,

    GROUP_CONCAT(DISTINCT r.route_name) AS routes

FROM physical_stops ps

JOIN improvement_opportunities io
    ON ps.id = io.physical_stop_id

LEFT JOIN physical_stop_members psm
    ON ps.id = psm.physical_stop_id

LEFT JOIN bus_stops bs
    ON psm.bus_stop_id = bs.id

LEFT JOIN stop_routes sr
    ON bs.id = sr.stop_id

LEFT JOIN routes r
    ON sr.route_id = r.id

WHERE ps.id = ?

GROUP BY ps.id

""",
(stop_id,)
)


    if not stop:
        return {"error": "Stop not found"}, 404


    row = stop[0]


    projects = []


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

    for rec_row in recommendations:

        recommendation_payload.append(
            {
                "type": rec_row[0],
                "priority": rec_row[1],
                "confidence": rec_row[2],
                "evidence": json.loads(rec_row[3]) if rec_row[3] else {},
                "reasons": json.loads(rec_row[4]) if rec_row[4] else []
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


    wmata_history = get_wmata_history(stop_id)

    wmata_evidence = get_wmata_evidence(stop_id)




    ddot_evidence = query_db(
        '''
        SELECT
            physical_stop_id,
            ddot_id,
            api_id,
            lifecycle_status,
            route_ids,
            route_count,
            confidence,
            notes
        FROM stop_ddot_shelter_evidence
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    ddot_evidence_payload = [
        {
            "physical_stop_id": row[0],
            "ddot_id": row[1],
            "api_id": row[2],
            "lifecycle_status": row[3],
            "routes": row[4].split(",") if row[4] else [],
            "route_count": row[5],
            "confidence": row[6],
            "notes": row[7]
        }
        for row in ddot_evidence
    ]



    ddot_interpretation = interpret_ddot_evidence(
        ddot_evidence_payload
    )


    impact_summary = query_db(
        """
        SELECT
            summary,
            impact_level,
            recommendations,
            opportunity_score,
            daily_route_exposure

        FROM stop_improvement_impact

        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )


    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS weekday_total,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM physical_stop_members psm

        JOIN stop_routes sr
            ON psm.bus_stop_id = sr.stop_id

        JOIN routes r
            ON sr.route_id = r.id

        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE psm.physical_stop_id = ?

        AND rs.period = (
            SELECT MAX(period)
            FROM ridership_snapshots
        )

        GROUP BY psm.physical_stop_id
        ''',
        (stop_id,)
    )



    rider_exposure = query_db(
        '''
        SELECT
            assessment_json

        FROM opportunity_assessments

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )

    rider_exposure_percentile = None

    if rider_exposure and rider_exposure[0][0]:

        try:

            assessment = json.loads(
                rider_exposure[0][0]
            )

            rider_exposure_percentile = (
                assessment.get(
                    "rider_exposure_percentile"
                )
            )

        except Exception:

            pass


    ridership_exposure = (
        {
            "weekday_boardings_total":
                round(ridership[0][0])
                if ridership[0][0]
                else 0,

            "average_weekday_boardings":
                round(ridership[0][0] / 23)
                if ridership[0][0]
                else 0,

            "route_count":
                ridership[0][1]
                or 0,

            "routes":
                ridership[0][2].split(",")
                if ridership[0][2]
                else []
        }
        if ridership
        else None
    )


    print("DEBUG STOP DETAIL ROW:", row)
    print("DEBUG TYPES:", type(row[1]), type(row[2]))

    road = get_road_index().nearest_road(
        row[2],
        row[1]
    )


    heading = 0

    if road and road["heading"] is not None:
        heading = road["heading"]


    streetview_url = (
        "https://www.google.com/maps/@?api=1"
        "&map_action=pano"
        f"&viewpoint={road['road_lat']},{road['road_lon']}"
        f"&heading={heading}"
        "&pitch=0"
        "&fov=90"
    )


    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS weekday_total,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM physical_stop_members psm

        JOIN stop_routes sr
            ON psm.bus_stop_id = sr.stop_id

        JOIN routes r
            ON sr.route_id = r.id

        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE psm.physical_stop_id = ?

        AND rs.period = (
            SELECT MAX(period)
            FROM ridership_snapshots
        )

        GROUP BY psm.physical_stop_id
        ''',
        (stop_id,)
    )


    ridership_exposure = (
        {
            "weekday_boardings_total":
                round(ridership[0][0])
                if ridership[0][0]
                else 0,

            "average_weekday_boardings":
                round(ridership[0][0] / 23)
                if ridership[0][0]
                else 0,

            "route_count":
                ridership[0][1]
                or 0,

            "routes":
                ridership[0][2].split(",")
                if ridership[0][2]
                else []
        }
        if ridership
        else None
    )


    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    print(
        "REVIEWER:",
        reviewer_id,
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    reviewer_history = query_db(
        """
        SELECT
            id,
            observed_at

        FROM stop_observations

        WHERE physical_stop_id=?

        AND reviewer_id=?

        AND source='community_review'

        ORDER BY observed_at DESC
        """,
        (
            stop_id,
            reviewer_id
        )
    )


    my_review_count = len(reviewer_history)


    total_stop_reviews = query_db(
        """
        SELECT COUNT(*)

        FROM stop_observations

        WHERE physical_stop_id=?

        AND source='community_review'
        """,
        (stop_id,)
    )


    community_review = {

        "has_reviewed": bool(reviewer_history),

        "my_review_count":
            my_review_count,

        "total_stop_reviews":
            total_stop_reviews[0][0]
            if total_stop_reviews
            else 0,

        "latest_review_id":
            reviewer_history[0][0]
            if reviewer_history
            else None,

        "last_reviewed_at":
            reviewer_history[0][1]
            if reviewer_history
            else None
    }


    opportunity = query_db(
        '''
        SELECT
            opportunity_score,
            impact_level,
            daily_route_exposure,
            summary,
            recommendations
        FROM stop_improvement_impact
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    opportunity_summary = (
        {
            "score":
                opportunity[0][0],

            "level":
                opportunity[0][1],

            "daily_route_exposure":
                opportunity[0][2],

            "summary":
                opportunity[0][3],

            "recommendations":
                json.loads(opportunity[0][4])
                if opportunity[0][4]
                else []
        }
        if opportunity
        else None
    )



    return jsonify(
        {
            "stop_id": stop_id,
            "location": row[0],
            "lat": row[1],
            "lon": row[2],
            "score": row[3],
            "impact": row[4],
            "routes":
                row[5].split(",")
                if row[5]
                else [],
            "heading": heading,
            "streetview_url": streetview_url,


            "wmata_evidence":
                wmata_evidence,


            "ddot_evidence":
                ddot_evidence_payload,

            "ddot_interpretation":
                ddot_interpretation,

            "community_review":
                community_review,

            "impact_summary":
                {
                    "rider_exposure_percentile":
                        rider_exposure_percentile,

                    "estimated_weekday_boardings":
                        ridership_exposure["average_weekday_boardings"]
                        if ridership_exposure
                        else None,

                    "routes_served":
                        ridership_exposure["route_count"]
                        if ridership_exposure
                        else 0,

                    "routes":
                        ridership_exposure["routes"]
                        if ridership_exposure
                        else [],

                    "opportunity_score":
                        opportunity_summary["score"]
                        if opportunity_summary
                        else None,

                    "impact_level":
                        opportunity_summary["level"]
                        if opportunity_summary
                        else None
                },


            "opportunity":
                opportunity_summary
        }
    )










@app.route("/review/start")
def review_start():

    scenario = request.args.get(
        "mode",
        request.args.get(
            "scenario",
            "opportunity"
        )
    )

    reviewer_key = session.get(
        "reviewer_key"
    )


    reviewer_id, reviewer_key = (
        get_or_create_reviewer(
            reviewer_key
        )
    )


    session["reviewer_key"] = reviewer_key


    stop_id_requested = request.args.get(
        "stop_id"
    )

    latitude = request.args.get("lat")
    longitude = request.args.get("lon")


    if stop_id_requested:

        result = assign_stop(
            reviewer_id,
            scenario,
            stop_id=int(stop_id_requested)
        )

    else:

        result = assign_stop(
            reviewer_id,
            scenario,
            latitude=latitude,
            longitude=longitude
        )


    if not result:
        return {
            "error": "No available review stops"
        }, 404


    assignment_id, stop_id = result


    return redirect(
        f"/review/{stop_id}?assignment_id={assignment_id}&mode={scenario}"
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
            state
        FROM physical_stops
        WHERE id=?
        """,
        (stop_id,)
    )

    if not stop:
        return "Stop not found", 404

    stop_row = list(stop[0])

    reviewer_key = session.get("reviewer_key")

    reviewer = None

    if reviewer_key:
        reviewer = query_db(
            """
            SELECT
                display_name
            FROM community_reviewers
            WHERE reviewer_key=?
            """,
            (reviewer_key,)
        )


    reviewer_name = (
        reviewer[0][0]
        if reviewer and reviewer[0][0]
        else None
    )


    return render_template(
        "review.html",
        stop=stop_row,
        stop_id=stop_id,
        survey_html=render_survey(),
        reviewer_name=reviewer_name
    )



@app.route("/review/<int:stop_id>/info")
def review_stop_info(stop_id):

    stop = query_db(
        """
        SELECT
            p.id,
            p.primary_name,
            p.latitude,
            p.longitude,
            p.state,
            p.dc_ward,
            p.dc_anc,
            p.county,
            p.municipality,

            w.wmata_stop_id,
            w.wmata_status,
            w.wmata_heading,
            w.wmata_bench,
            w.wmata_shelter,
            w.wmata_accessible,
            w.match_distance_m,
            w.match_confidence

        FROM physical_stops p

        LEFT JOIN active_wmata_evidence w
        ON p.id = w.physical_stop_id

        WHERE p.id=?
        """,
        (stop_id,)
    )

    if not stop:
        return {"error": "Stop not found"}, 404

    row = stop[0]



    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS total_weekday_boardings,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM physical_stop_members psm

        JOIN stop_routes sr
            ON psm.bus_stop_id = sr.stop_id

        JOIN routes r
            ON sr.route_id = r.id

        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE psm.physical_stop_id = ?

        AND rs.period = (
            SELECT MAX(period)
            FROM ridership_snapshots
        )

        GROUP BY psm.physical_stop_id
        ''',
        (stop_id,)
    )


    ridership_exposure = (
        {
            "average_weekday_boardings":
                round(ridership[0][0] / 23)
                if ridership[0][0]
                else 0,

            "route_count":
                ridership[0][1]
                or 0,

            "routes":
                ridership[0][2].split(",")
                if ridership[0][2]
                else []
        }
        if ridership
        else None
    )



    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS weekday_total,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM physical_stop_members psm

        JOIN stop_routes sr
            ON psm.bus_stop_id = sr.stop_id

        JOIN routes r
            ON sr.route_id = r.id

        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE psm.physical_stop_id = ?

        AND rs.period = (
            SELECT MAX(period)
            FROM ridership_snapshots
        )

        GROUP BY psm.physical_stop_id
        ''',
        (stop_id,)
    )


    ridership_exposure = (
        {
            "weekday_boardings_total":
                round(ridership[0][0])
                if ridership[0][0]
                else 0,

            "average_weekday_boardings":
                round(ridership[0][0] / 23)
                if ridership[0][0]
                else 0,

            "route_count":
                ridership[0][1]
                or 0,

            "routes":
                ridership[0][2].split(",")
                if ridership[0][2]
                else []
        }
        if ridership
        else None
    )


    impact_summary = query_db(
        '''
        SELECT
            summary,
            impact_level,
            recommendations,
            opportunity_score,
            daily_route_exposure

        FROM stop_improvement_impact

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    rider_exposure = query_db(
        '''
        SELECT
            assessment_json

        FROM opportunity_assessments

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    rider_exposure_percentile = None


    if rider_exposure and rider_exposure[0][0]:

        try:

            assessment = json.loads(
                rider_exposure[0][0]
            )

            rider_exposure_percentile = (
                assessment.get(
                    "rider_exposure_percentile"
                )
            )

        except Exception:

            pass



    opportunity = query_db(
        '''
        SELECT
            opportunity_score,
            impact_level,
            daily_route_exposure,
            summary,
            recommendations
        FROM stop_improvement_impact
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    opportunity_summary = (
        {
            "score":
                opportunity[0][0],

            "level":
                opportunity[0][1],

            "daily_route_exposure":
                opportunity[0][2],

            "summary":
                opportunity[0][3],

            "recommendations":
                json.loads(opportunity[0][4])
                if opportunity[0][4]
                else []
        }
        if opportunity
        else None
    )



    streetview = get_road_index().nearest_road(
        row[2],
        row[3]
    )

    heading = None

    if streetview and streetview["heading"] is not None:
        heading = streetview["heading"]


    streetview_url = (
        "https://www.google.com/maps/@?"
        f"api=1&map_action=pano"
        f"&viewpoint={row[2]},{row[3]}"
        f"&heading={heading or 0}"
    )


    community_reviews = query_db(
        """
        SELECT
            id,
            observed_at,
            shelter_present,
            bench_present,
            notes
        FROM stop_observations
        WHERE physical_stop_id=?
        AND source='community_review'
        ORDER BY observed_at DESC
        """,
        (stop_id,)
    )


    return jsonify(
        {
            "stop_id": row[0],
            "name": row[1],
            "lat": row[2],
            "lon": row[3],
            "state": row[4],
            "jurisdiction": row[4],
            "ward": row[5],
            "anc": row[6],
            "county": row[7],
            "municipality": row[8],

            "serving_direction":
                row[11],

            "streetview_url": streetview_url,

            "wmata": {
                "availability":
                    "confirmed"
                    if row[9]
                    else "unavailable",

                "stop_id": row[9],
                "status": row[10],
                "bench": row[12],
                "shelter": row[13],
                "accessible": row[14],
                "match_distance_m": row[15],
                "match_confidence": row[16]
            },

            "wmata_evidence": {
                "wmata_stop_id": row[9],
                "wmata_status": row[10],
                "wmata_heading": row[11],
                "wmata_bench": row[12],
                "wmata_shelter": row[13],
                "wmata_accessible": row[14],
                "match_distance_m": row[15],
                "match_confidence": row[16]
            },


            "community_reviews": {
                "review_count": len(community_reviews),

                "reviews": [
                    {
                        "id": review[0],
                        "date": review[1],
                        "shelter": review[2],
                        "bench": review[3],
                        "notes": review[4].strip() if review[4] else ""
                    }
                    for review in community_reviews
                ]
            },


            "ridership_exposure":
                ridership_exposure,

            "impact_summary":
                {
                    "rider_exposure_percentile":
                        rider_exposure_percentile,

                    "estimated_weekday_boardings":
                        ridership_exposure["average_weekday_boardings"]
                        if ridership_exposure
                        else None,

                    "routes_served":
                        ridership_exposure["route_count"]
                        if ridership_exposure
                        else 0,

                    "routes":
                        ridership_exposure["routes"]
                        if ridership_exposure
                        else [],

                    "opportunity_score":
                        opportunity_summary["score"]
                        if opportunity_summary
                        else None,

                    "impact_level":
                        opportunity_summary["level"]
                        if opportunity_summary
                        else None
                },


            "opportunity":
                opportunity_summary
        }
    )





@app.route("/review/<int:stop_id>/assignment")
def review_assignment(stop_id):

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    assignment_id = request.args.get(
        "assignment_id"
    )


    if assignment_id:

        assignment = query_db(
            """
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE id=?
            """,
            (
                assignment_id,
            )
        )

    else:

        assignment = query_db(
            """
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?
            AND reviewer_id=?
            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            """,
            (
                stop_id,
                reviewer_id
            )
        )


    if not assignment:

        scenario = request.args.get(
            "mode",
            "opportunity"
        )

        query_db(
            """
            INSERT INTO stop_review_assignments
            (
                stop_id,
                reviewer_id,
                scenario,
                status
            )

            VALUES (?, ?, ?, 'assigned')
            """,
            (
                stop_id,
                reviewer_id,
                scenario
            )
        )


        assignment = query_db(
            """
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?
            AND reviewer_id=?
            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            """,
            (
                stop_id,
                reviewer_id
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




@app.route("/stops/<int:stop_id>/community-reviews")
def community_reviews(stop_id):

    reviews = query_db(
        """
        SELECT
            id,
            observed_at,
            shelter_present,
            bench_present,
            notes,
            reviewer_id
        FROM stop_observations
        WHERE physical_stop_id=?
        AND source='community_review'
        ORDER BY observed_at DESC
        """,
        (stop_id,)
    )


    return jsonify(
        {
            "review_count":
                len(reviews),

            "reviews":
                [
                    {
                        "id": row[0],
                        "date": row[1],
                        "shelter": row[2],
                        "bench": row[3],
                        "notes": row[4]
                    }
                    for row in reviews
                ]
        }
    )


@app.route("/review/submit", methods=["POST"])
def submit_review():

    data = request.json

    print(
        "SUBMIT DATA:",
        data
    )


    if isinstance(data.get("seating_type"), list):
        data["seating_type"] = ",".join(
            data["seating_type"]
        )



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

    if isinstance(data.get("usage_times"), list):
        data["usage_times"] = ",".join(
            data["usage_times"]
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
    assignment_id = data.get("assignment_id")


    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    display_name = data.get(
        "display_name",
        ""
    ).strip()


    if display_name:

        query_db(
            """
            UPDATE community_reviewers
            SET
                display_name=?,
                profile_created_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                display_name,
                reviewer_id
            )
        )



    if not assignment_id:
        return {
            "error": "valid assignment_id required"
        }, 400


    existing_review = query_db(
        """
        SELECT id
        FROM stop_observations
        WHERE physical_stop_id=?
        AND reviewer_id=?
        AND source='community_review'
        LIMIT 1
        """,
        (
            stop_id,
            reviewer_id
        )
    )


    review_action = data.get(
        "review_action",
        "new"
    )


    if existing_review and review_action == "update":

        query_db(
            """
            UPDATE stop_observations
            SET
                shelter_present=?,
                bench_present=?,
                trash_present=?,
                bench_feasible=?,
                ada_clearance_possible=?,
                notes=?,
                observed_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data.get("shelter_present"),
                data.get("bench_present"),
                data.get("trash_present"),
                data.get("bench_feasible"),
                data.get("ada_clearance_possible"),
                data.get("notes"),
                existing_review[0][0]
            )
        )


        return {
            "success": True,
            "message": "Review updated",
            "stop_id": stop_id
        }




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


    review_count = query_db(
        """
        SELECT COUNT(*)
        FROM stop_review_assignments
        WHERE reviewer_id=?
        AND status='completed'
        """,
        (reviewer_id,)
    )[0][0]


    first_review = (
        query_db(
            """
            SELECT COUNT(*)
            FROM stop_review_assignments
            WHERE stop_id=?
            AND status='completed'
            """,
            (stop_id,)
        )[0][0]
        == 1
    )


    impact = query_db(
        """
        SELECT
            daily_route_exposure
        FROM stop_improvement_impact
        WHERE physical_stop_id=?
        """,
        (stop_id,)
    )


    return {
        "success": True,
        "stop_id": stop_id,
        "assignment_id": assignment_id,
        "reviewer_id": reviewer_id,

        "reviewer_stats": {

            "display_name":
                query_db(
                    """
                    SELECT display_name
                    FROM community_reviewers
                    WHERE id=?
                    """,
                    (reviewer_id,)
                )[0][0],

            "review_count":
                review_count,

            "first_review":
                first_review,

            "stops_reviewed":
                query_db(
                    """
                    SELECT COUNT(DISTINCT stop_id)
                    FROM stop_review_assignments
                    WHERE reviewer_id=?
                    AND status='completed'
                    """,
                    (reviewer_id,)
                )[0][0],


            "stewarded_stops":
                query_db(
                    """
                    SELECT COUNT(DISTINCT stop_id)
                    FROM community_stewardships
                    WHERE reviewer_id=?
                    """,
                    (reviewer_id,)
                )[0][0],

            "total_route_boardings_represented":
                round(
                    query_db(
                        """
                        SELECT
                            COALESCE(
                                SUM(unique_stops.daily_route_exposure),
                                0
                            )

                        FROM (

                            SELECT DISTINCT
                                sra.stop_id,
                                si.daily_route_exposure

                            FROM stop_review_assignments sra

                            LEFT JOIN stop_improvement_impact si

                            ON sra.stop_id =
                               si.physical_stop_id

                            WHERE sra.reviewer_id=?

                            AND sra.status='completed'

                        ) unique_stops
                        """,
                        (reviewer_id,)
                    )[0][0]
                ),

            "routes_covered":
                (
                    query_db(
                        """
                        SELECT
                            GROUP_CONCAT(
                                DISTINCT r.route_id
                            )

                        FROM stop_review_assignments sra

                        JOIN physical_stop_members psm
                        ON sra.stop_id =
                           psm.physical_stop_id

                        JOIN stop_routes sr
                        ON psm.bus_stop_id =
                           sr.stop_id

                        JOIN routes r
                        ON sr.route_id = r.id

                        WHERE sra.reviewer_id=?

                        AND sra.status='completed'
                        """,
                        (reviewer_id,)
                    )[0][0].split(",")
                    if query_db(
                        """
                        SELECT
                            GROUP_CONCAT(
                                DISTINCT r.route_id
                            )

                        FROM stop_review_assignments sra

                        JOIN physical_stop_members psm
                        ON sra.stop_id =
                           psm.physical_stop_id

                        JOIN stop_routes sr
                        ON psm.bus_stop_id =
                           sr.stop_id

                        JOIN routes r
                        ON sr.route_id = r.id

                        WHERE sra.reviewer_id=?

                        AND sra.status='completed'
                        """,
                        (reviewer_id,)
                    )[0][0]
                    else []
                )

        },

"community_impact": {

    "daily_route_exposure":
        impact[0][0]
        if impact
        else None,

    "routes":
        (
            query_db(
                """
                SELECT
                    GROUP_CONCAT(DISTINCT r.route_id)

                FROM physical_stop_members psm

                JOIN stop_routes sr
                    ON psm.bus_stop_id = sr.stop_id

                JOIN routes r
                    ON sr.route_id = r.id

                WHERE psm.physical_stop_id=?

                """,
                (stop_id,)
            )[0][0].split(",")
            if query_db(
                """
                SELECT
                    GROUP_CONCAT(DISTINCT r.route_id)

                FROM physical_stop_members psm

                JOIN stop_routes sr
                    ON psm.bus_stop_id = sr.stop_id

                JOIN routes r
                    ON sr.route_id = r.id

                WHERE psm.physical_stop_id=?

                """,
                (stop_id,)
            )[0][0]
            else []
        )
    },

"stewardships": {

    "count":
        query_db(
            """
            SELECT COUNT(*)
            FROM community_stewardships
            WHERE reviewer_id=?
            """,
            (reviewer_id,)
        )[0][0],


    "stops":
        [
            {
                "stop_id": row[0],
                "name": row[1]
            }

            for row in query_db(
                """
                SELECT
                    cs.stop_id,
                    p.primary_name

                FROM community_stewardships cs

                JOIN physical_stops p
                    ON cs.stop_id = p.id

                WHERE cs.reviewer_id=?

                ORDER BY cs.created_at DESC
                """,
                (reviewer_id,)
            )
        ]

}

}


def get_reviewer_impact(reviewer_id):

    return query_db(
        """
        SELECT
            COUNT(DISTINCT sra.stop_id),
            COALESCE(SUM(si.daily_route_exposure),0)

        FROM stop_review_assignments sra

        LEFT JOIN stop_improvement_impact si
            ON sra.stop_id = si.physical_stop_id

        WHERE sra.reviewer_id=?

        AND sra.status='completed'

        """,
        (reviewer_id,)
    )[0]




@app.route("/api/review-queue")
def review_queue():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            rq.physical_stop_id,
            ps.latitude AS lat,
            ps.longitude AS lon,
            rq.priority_rank,
            rq.opportunity_score,
            rq.location_name,
            rq.review_status,
            rq.consensus_status

        FROM review_queue rq

        JOIN physical_stops ps
            ON ps.id = rq.physical_stop_id

        WHERE rq.review_status = 'pending'

        ORDER BY
            rq.priority_rank,
            rq.physical_stop_id

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
                    "location_name": row["location_name"],
                    "priority_rank": row["priority_rank"],
                    "opportunity_score": row["opportunity_score"],
                    "review_status": row["review_status"],
                    "consensus_status": row["consensus_status"]
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
            io.opportunity_score,

            CASE
                WHEN io.opportunity_score >= 80 THEN 'very_high'
                WHEN io.opportunity_score >= 60 THEN 'high'
                WHEN io.opportunity_score >= 40 THEN 'medium'
                ELSE 'low'
            END AS impact

        FROM improvement_opportunities io

        JOIN physical_stops ps
            ON io.physical_stop_id = ps.id

        ORDER BY io.opportunity_score DESC

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
                "impact": row[4]
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


@app.route("/geography/dc-ancs")
def geography_dc_ancs():

    dc_ward = request.args.get("dc_ward")
    dc_anc = request.args.get("dc_anc")


    rows = query_db(
        """
        SELECT DISTINCT dc_anc
        FROM stop_jurisdiction
        WHERE dc_anc IS NOT NULL

        AND (
            ? IS NULL
            OR dc_ward = ?
        )

        ORDER BY dc_anc
        """,
        (
            dc_ward,
            dc_ward
        )
    )


    return jsonify(
        [
            row[0]
            for row in rows
        ]
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
    dc_anc = request.args.get("dc_anc")

    review_mode = request.args.get("review")
    action_filter = request.args.get("action")


    if route:

        rows = query_db(
            """
            SELECT DISTINCT

                ps.id,
                GROUP_CONCAT(DISTINCT we.wmata_stop_id),
                ps.primary_name,
                ps.latitude AS lat,
                ps.longitude AS lon,
                io.opportunity_score,

                CASE
                    WHEN io.opportunity_score >= 80 THEN 'very_high'
                    WHEN io.opportunity_score >= 60 THEN 'high'
                    WHEN io.opportunity_score >= 40 THEN 'medium'
                    ELSE 'low'
                END,

                CASE
                    WHEN io.opportunity_score >= 80 THEN 'very_high'
                    WHEN io.opportunity_score >= 60 THEN 'high'
                    WHEN io.opportunity_score >= 40 THEN 'medium'
                    ELSE 'low'
                END,

                COALESCE(
                    ca.confidence,
                    'needs_validation'
                ),

                'none'

            FROM physical_stops ps

            JOIN active_wmata_evidence aw
                ON ps.id = aw.physical_stop_id

            JOIN improvement_opportunities io
                ON ps.id = io.physical_stop_id

            JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            JOIN bus_stops bs
                ON psm.bus_stop_id = bs.id

            JOIN stop_routes sr
                ON bs.id = sr.stop_id

            LEFT JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            LEFT JOIN stop_consensus ca
                ON ps.id = ca.stop_id

            LEFT JOIN stop_jurisdiction sj
                ON ps.id = sj.stop_id

            WHERE sr.route_id = ?

            GROUP BY
                ps.id

            ORDER BY io.opportunity_score DESC;

            """,
            (
                route,
            )
        )

    else:

        rows = query_db(
            """
            SELECT DISTINCT

                ps.id,
                GROUP_CONCAT(DISTINCT we.wmata_stop_id),
                ps.primary_name,
                ps.latitude AS lat,
                ps.longitude AS lon,
                io.opportunity_score,
                
    CASE
        WHEN io.opportunity_score >= 80 THEN 'very_high'
        WHEN io.opportunity_score >= 60 THEN 'high'
        WHEN io.opportunity_score >= 40 THEN 'medium'
        ELSE 'low'
    END
    ,
                
    CASE
        WHEN io.opportunity_score >= 80 THEN 'very_high'
        WHEN io.opportunity_score >= 60 THEN 'high'
        WHEN io.opportunity_score >= 40 THEN 'medium'
        ELSE 'low'
    END
    ,
                COALESCE(
                    ca.confidence,
                    'needs_validation'
                ),

                COALESCE(
                    'none',
                    'none'
                )

            FROM physical_stops ps

            JOIN active_wmata_evidence aw
                ON ps.id = aw.physical_stop_id

            LEFT JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            LEFT JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            JOIN improvement_opportunities io
                ON ps.id = io.physical_stop_id

            
            LEFT JOIN stop_consensus ca
                ON ps.id = ca.stop_id

            LEFT JOIN stop_jurisdiction sj
                ON ps.id = sj.stop_id

            WHERE (
                ? IS NULL
                OR (
                    ? = 'high'
                    AND 
                    CASE
                        WHEN io.opportunity_score >= 80 THEN 'very_high'
                        WHEN io.opportunity_score >= 60 THEN 'high'
                        WHEN io.opportunity_score >= 40 THEN 'medium'
                        ELSE 'low'
                    END IN ('high', 'very_high')
        
                )
                OR (
                    ? = 'very_high'
                    AND 
                    CASE
                        WHEN io.opportunity_score >= 80 THEN 'very_high'
                        WHEN io.opportunity_score >= 60 THEN 'high'
                        WHEN io.opportunity_score >= 40 THEN 'medium'
                        ELSE 'low'
                    END = 'very_high'
        
                )
            )

            AND (
                ? IS NULL
                OR 
                    CASE
                        WHEN io.opportunity_score >= 80 THEN 'very_high'
                        WHEN io.opportunity_score >= 60 THEN 'high'
                        WHEN io.opportunity_score >= 40 THEN 'medium'
                        ELSE 'low'
                    END = ?
        
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
                OR sj.dc_anc = ?
            )

            AND (
                ? IS NULL

                OR (
                    ? = 'opportunity'
                    AND (
                        ca.confidence IS NULL
                        OR ca.confidence = 'needs_validation'
                    )
                )

                OR (
                    ? = 'candidate'
                    AND ca.confidence = 'validated'
                )
            )

            AND (
                ? IS NULL
                OR 'none' = ?
            )

            GROUP BY
                ps.id,
                ps.primary_name,
                ps.latitude,
                ps.longitude,
                io.opportunity_score,
                ca.confidence

            ORDER BY io.opportunity_score DESC;
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
                dc_anc,
                dc_anc,
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
                            row[4],
                            row[3]
                        ]
                    },

                    "properties": {
                        "stop_id": row[0],
                        "wmata_stop_ids": (
                            row[1].split(",")
                            if row[1]
                            else []
                        ),
                        "location": row[2],
                        "score": row[5],
                        "impact": row[6],
                        "priority": row[7],
                        "validation_status": row[8],
                        "action_status": row[9]
                    }
                }

                for row in rows
            ]
        }
    )







@app.route("/stops/<int:stop_id>/steward", methods=["POST"])
def create_stewardship(stop_id):

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    query_db(
        """
        INSERT OR IGNORE INTO community_stewardships
        (
            reviewer_id,
            stop_id
        )
        VALUES (?, ?)
        """,
        (
            reviewer_id,
            stop_id
        )
    )


    return jsonify(
        {
            "status": "stewarded",
            "stop_id": stop_id
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
        FROM stop_observations
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
        FROM stop_observations
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
            confidence,
            COUNT(*) AS count
        FROM stop_consensus
        GROUP BY confidence
        ORDER BY count DESC
        """
    )

    return jsonify(
        [
            {
                "confidence": row[0],
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





@app.route("/reviewer/routes")
def reviewer_routes():

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    routes = query_db(
        """
        SELECT
            route_id,
            route_name

        FROM routes

        ORDER BY route_id
        """
    )


    selected = query_db(
        """
        SELECT route_id

        FROM community_reviewer_routes

        WHERE reviewer_id=?
        """,
        (
            reviewer_id,
        )
    )


    return jsonify(
        {
            "routes":
                [
                    {
                        "route_id": r[0],
                        "route_name": r[1]
                    }
                    for r in routes
                ],

            "selected":
                [
                    r[0]
                    for r in selected
                ]
        }
    )



@app.route(
    "/reviewer/routes",
    methods=["POST"]
)
def save_reviewer_routes():

    data = request.get_json()

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    routes = data.get(
        "routes",
        []
    )


    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cur = conn.cursor()


    cur.execute(
        """
        DELETE FROM community_reviewer_routes

        WHERE reviewer_id=?
        """,
        (
            reviewer_id,
        )
    )


    for route in routes:

        cur.execute(
            """
            INSERT INTO community_reviewer_routes
            (
                reviewer_id,
                route_id
            )

            VALUES (?,?)
            """,
            (
                reviewer_id,
                route
            )
        )


    conn.commit()
    conn.close()


    return jsonify(
        {
            "success": True,
            "routes": routes
        }
    )



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
    ON sr.stop_id = bs.id

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


@app.route("/api/reviewer/status")
def reviewer_status():

    reviewer_key = session.get(
        "reviewer_key"
    )


    if not reviewer_key:

        return jsonify(
            {
                "has_profile": False
            }
        )


    reviewer = query_db(
        """
        SELECT
            display_name
        FROM community_reviewers
        WHERE reviewer_key=?
        """,
        (reviewer_key,)
    )


    if not reviewer:

        return jsonify(
            {
                "has_profile": False
            }
        )


    return jsonify(
        {
            "has_profile": True,
            "display_name":
                reviewer[0][0]
                if reviewer[0][0]
                else "Community Volunteer"
        }
    )




@app.route("/reviewer/profile")
def reviewer_profile_page():

    return render_template(
        "reviewer_profile.html"
    )



@app.route("/api/reviewer/profile")
def reviewer_profile_api():

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    reviewer = query_db(
        """
        SELECT display_name
        FROM community_reviewers
        WHERE id=?
        """,
        (reviewer_id,)
    )


    stewarded = query_db(
        """
        SELECT
            cs.stop_id,
            p.primary_name,
            p.state,
            p.county,
            p.municipality

        FROM community_stewardships cs

        JOIN physical_stops p
            ON cs.stop_id = p.id

        WHERE cs.reviewer_id=?

        ORDER BY p.primary_name

        """,
        (reviewer_id,)
    )


    stats = {

        "reviews_completed":
            query_db(
                """
                SELECT COUNT(*)
                FROM stop_review_assignments
                WHERE reviewer_id=?
                AND status='completed'
                """,
                (reviewer_id,)
            )[0][0],


        "stops_reviewed":
            query_db(
                """
                SELECT COUNT(DISTINCT stop_id)
                FROM stop_review_assignments
                WHERE reviewer_id=?
                AND status='completed'
                """,
                (reviewer_id,)
            )[0][0],


        "ridership_impacted":
            query_db(
                """
                SELECT
                    COALESCE(
                        SUM(unique_stops.daily_route_exposure),
                        0
                    )

                FROM (

                    SELECT DISTINCT
                        sra.stop_id,
                        si.daily_route_exposure

                    FROM stop_review_assignments sra

                    LEFT JOIN stop_improvement_impact si
                    ON sra.stop_id =
                       si.physical_stop_id

                    WHERE sra.reviewer_id=?

                    AND sra.status='completed'

                ) unique_stops
                """,
                (reviewer_id,)
            )[0][0],


        "stewarded_stops":

            len(stewarded),


        "routes_covered":

            (
                query_db(
                    """
                    SELECT
                        GROUP_CONCAT(
                            DISTINCT r.route_id
                        )

                    FROM stop_review_assignments sra

                    JOIN physical_stop_members psm
                    ON sra.stop_id =
                       psm.physical_stop_id

                    JOIN stop_routes sr
                    ON psm.bus_stop_id =
                       sr.stop_id

                    JOIN routes r
                    ON sr.route_id = r.id

                    WHERE sra.reviewer_id=?

                    AND sra.status='completed'

                    """,
                    (reviewer_id,)
                )[0][0].split(",")
                if query_db(
                    """
                    SELECT
                        GROUP_CONCAT(
                            DISTINCT r.route_id
                        )

                    FROM stop_review_assignments sra

                    JOIN physical_stop_members psm
                    ON sra.stop_id =
                       psm.physical_stop_id

                    JOIN stop_routes sr
                    ON psm.bus_stop_id =
                       sr.stop_id

                    JOIN routes r
                    ON sr.route_id = r.id

                    WHERE sra.reviewer_id=?

                    AND sra.status='completed'

                    """,
                    (reviewer_id,)
                )[0][0]
                else []
            )

    }



    routes = query_db(
        """
        SELECT
            GROUP_CONCAT(DISTINCT r.route_id)

        FROM stop_review_assignments sra

        JOIN physical_stop_members psm
            ON sra.stop_id = psm.physical_stop_id

        JOIN stop_routes sr
            ON psm.bus_stop_id = sr.stop_id

        JOIN routes r
            ON sr.route_id = r.id

        WHERE sra.reviewer_id=?

        AND sra.status='completed'
        """,
        (reviewer_id,)
    )


    return jsonify(
        {
            "display_name":
                reviewer[0][0]
                if reviewer and reviewer[0][0]
                else None,


            "stats":
                stats,


            "stewarded_stops":
                [
                    {
                        "stop_id": row[0],
                        "name": row[1],
                        "state": row[2],
                        "county": row[3],
                        "municipality": row[4]
                    }

                    for row in stewarded
                ]
        }
    )



@app.route("/review/routes")
def review_routes():

    return render_template(
        "review_routes.html"
    )



@app.route("/dashboard")
def dashboard():

    return render_template(
        "dashboard.html"
    )




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

        LEFT JOIN active_wmata_evidence w
        ON p.id=w.physical_stop_id

        LEFT JOIN stop_osm_evidence o
        ON p.id=o.stop_id

        """
    )[0]


    return {
        "total": summary[0] if isinstance(summary, tuple) else summary.get("total", 0),
        "likely_shelter": summary[1] if isinstance(summary, tuple) else summary.get("likely_shelter", 0),
        "likely_bench": summary[2] if isinstance(summary, tuple) else summary.get("likely_bench", 0),
        "no_shelter_evidence": summary[3] if isinstance(summary, tuple) else summary.get("no_shelter_evidence", 0)
    }



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



            shelter_count = count("""
            SELECT COUNT(DISTINCT p.id)
            FROM physical_stops p
            WHERE p.id IN ({})
            AND EXISTS (
                SELECT 1
                FROM active_wmata_evidence w
                WHERE w.physical_stop_id = p.id
                AND w.wmata_shelter = 1
            )
            """)


            bench_count = count("""
            SELECT COUNT(DISTINCT p.id)
            FROM physical_stops p
            WHERE p.id IN ({})
            AND EXISTS (
                SELECT 1
                FROM active_wmata_evidence w
                WHERE w.physical_stop_id = p.id
                AND w.wmata_bench = 1
            )
            """)


            known_amenity_count = count("""
            SELECT COUNT(DISTINCT p.id)
            FROM physical_stops p
            WHERE p.id IN ({})
            AND EXISTS (
                SELECT 1
                FROM active_wmata_evidence w
                WHERE w.physical_stop_id = p.id
                AND (
                    w.wmata_shelter = 1
                    OR w.wmata_bench = 1
                )
            )
            """)


            rows.append(
                {
                    "type": geo_type,

                    "geography": name,

                    "total_stops": len(stops),

                    "shelter_likely_confirmed":
                        shelter_count,

                    "bench_likely_confirmed":
                        bench_count,

                    "amenity_status_unknown":
                        len(stops) - known_amenity_count
                }
            )


    conn.close()

    return jsonify(rows)





@app.route("/handbook")
def community_handbook():

    from pathlib import Path
    import markdown

    path = Path("docs/DMV_Bus_Stop_Intelligence_Handbook.md")

    html = markdown.markdown(
        path.read_text(),
        extensions=["tables"]
    )

    return html



@app.route("/volunteer-handbook")
def volunteer_handbook():

    from pathlib import Path
    import markdown

    path = Path("docs/Volunteer_Review_Handbook.md")

    html = markdown.markdown(
        path.read_text(),
        extensions=["tables"]
    )

    return html






@app.route("/test-route")
def test_route():
    return "hello"


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
        use_reloader=False
    )


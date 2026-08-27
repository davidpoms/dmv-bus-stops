import json
import os
import sqlite3
import secrets
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

"""
DMV Bus Stops Improvement API
"""

from flask import Flask, jsonify, send_from_directory, request, render_template, redirect, session, url_for
import calendar
import math
from datetime import datetime, timedelta


from src.review.assignment_router import (
    get_or_create_reviewer,
    assign_stop,
    normalize_campaign,
)

from src.assessment.interpretation import (
    interpret_ddot_evidence,
    summarize_stop_evidence,
    generate_review_action_summary,
    interpret_bench_status,
    interpret_review_priority,
)

from src.review.consensus import calculate_stop_consensus
from src.review.context import build_review_context
from src.review.auth import (
    TOKEN_LIFETIME_MINUTES, RateLimitError, consume_login_token,
    enforce_login_rate_limits, invalidate_login_token, issue_login_token,
    normalize_email, supersede_login_tokens,
)
from src.review.email_delivery import (
    EmailConfigurationError, email_delivery_status, smtp_sender_from_env,
)
from src.amenities.status_synthesis import geography_status_rows
from src.amenities.review_priority import refresh_after_community_mutation
from src.processing.serving_directions import serving_directions_for_stop


app = Flask(
    __name__,
    static_folder=None,
    template_folder="../dashboard/templates"
)

app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)


@app.context_processor
def pilot_template_configuration():
    return {"pilot_support_contact": os.environ.get("PILOT_SUPPORT_CONTACT", "").strip()}


@app.before_request
def require_deployment_secret():
    if not app.secret_key and not app.testing:
        return {
            "error": "FLASK_SECRET_KEY must be configured before serving requests",
            "code": "server_configuration_required",
        }, 503


@app.after_request
def log_operational_failure(response):
    if response.status_code >= 400 and (
        request.path == "/review/submit" or request.path.startswith("/reviewer/")
    ):
        app.logger.warning(
            "pilot_request_failed method=%s path=%s status=%s",
            request.method, request.path, response.status_code,
        )
    return response

DATABASE_PATH = Path(
    os.environ.get(
        "DMV_BUS_STOPS_DB",
        BASE_DIR / "src" / "database" / "dmv_bus_stops.db",
    )
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
            match_confidence,
            match_distance_m

        FROM stop_wmata_evidence

        WHERE physical_stop_id = ?

        ORDER BY match_distance_m ASC

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


def latest_ridership_weekdays():
    rows = query_db("SELECT MAX(period) FROM ridership_snapshots")
    if not rows or not rows[0][0]:
        return 0
    period = datetime.strptime(rows[0][0], "%Y-%m-%d")
    return sum(
        datetime(period.year, period.month, day).weekday() < 5
        for day in range(1, calendar.monthrange(period.year, period.month)[1] + 1)
    )


def get_current_amenity_evidence(stop_id):
    """Return normalized evidence allowed in current public amenity views."""
    return query_db(
        """
        SELECT
            id,
            source,
            source_record_id,
            amenity_type,
            present,
            confidence,
            match_distance_m,
            notes,
            jurisdiction,
            value
        FROM stop_amenity_evidence
        WHERE physical_stop_id=?
          AND source != 'DDOT'
        ORDER BY created_at DESC, id DESC
        """,
        (stop_id,)
    )


def get_current_amenity_status(stop_id):
    """Return canonical derived status when the rebuild has been applied."""
    table_exists = query_db(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='stop_amenity_status'
        """
    )
    if not table_exists:
        return []
    columns = {row[1] for row in query_db("PRAGMA table_info(stop_amenity_status)")}
    optional = {
        "local_yes_sources": "'[]'",
        "local_no_sources": "'[]'",
        "osm_yes": "0",
        "osm_no": "0",
        "community_yes_count": "0",
        "community_no_count": "0",
    }
    optional_select = ", ".join(
        name if name in columns else f"{fallback} AS {name}"
        for name, fallback in optional.items()
    )
    return query_db(
        f"""
        SELECT amenity_type, derived_status, consensus_status,
               evidence_conflict, consensus_conflicts_with_other_evidence,
               rationale, updated_at, {optional_select}
        FROM stop_amenity_status
        WHERE physical_stop_id=?
        ORDER BY CASE amenity_type WHEN 'shelter' THEN 1 ELSE 2 END
        """,
        (stop_id,)
    )


def compass_heading_label(value):
    """Translate a numeric stop heading to the same eight-point UI label."""
    try:
        degrees = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(degrees):
        return None
    degrees %= 360
    labels = (
        "Northbound", "Northeast", "Eastbound", "Southeast",
        "Southbound", "Southwest", "Westbound", "Northwest",
    )
    return labels[round(degrees / 45) % 8]


def get_serving_directions(stop_id):
    """Return headings explicitly linked to source members of a physical stop.

    ``stop_wmata_evidence.physical_stop_id`` was populated by an unbounded
    nearest-neighbor import, so it is not sufficient proof that a heading
    describes this boarding location.  The GTFS/member identity chain is the
    eligibility rule; unexplained WMATA status codes are provenance only.
    """
    tables = query_db(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
        "('stop_wmata_evidence','physical_stop_members','gtfs_stop_map','bus_stops')"
    )
    if len(tables) != 4:
        return []
    evidence_columns = {
        row[1] for row in query_db("PRAGMA table_info(stop_wmata_evidence)")
    }
    if not {
        "id", "wmata_stop_id", "wmata_heading", "wmata_status",
        "match_distance_m", "match_confidence", "created_at",
    } <= evidence_columns:
        return []
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        by_member = serving_directions_for_stop(conn, stop_id)
        source_ids = dict(conn.execute(
            """SELECT pm.bus_stop_id,b.external_stop_id
               FROM physical_stop_members pm
               JOIN bus_stops b ON b.id=pm.bus_stop_id
               WHERE pm.physical_stop_id=?""",
            (stop_id,),
        ))
    finally:
        conn.close()
    directions = []
    for member_stop_id, member_directions in by_member.items():
        for direction in member_directions:
            heading = format(direction["heading_degrees"], "g")
            directions.append({
                "heading_degrees": heading,
                "compass_label": compass_heading_label(heading),
                "wmata_stop_id": direction["gtfs_stop_id"],
                "member_stop_id": member_stop_id,
                "source_stop_id": source_ids.get(member_stop_id),
                "linkage_method": direction["linkage_method"],
                "evidence_status": direction["evidence_status"],
                "match_distance_m": direction["match_distance_m"],
                "confidence": direction["confidence"],
            })
    return sorted(directions, key=lambda item: (
        float(item["heading_degrees"]), item["heading_degrees"],
        item["wmata_stop_id"], item["member_stop_id"],
    ))


def get_serving_headings(stop_id):
    """Compatibility projection of the validated serving-direction records."""
    return [item["heading_degrees"] for item in get_serving_directions(stop_id)]


def build_amenity_status_payload(status_rows, evidence_rows):
    """Attach only the evidence that contributes to each canonical conclusion."""
    local_records = []
    for row in evidence_rows:
        value = str(row[9] or "").strip().lower()
        claim = (
            "present" if value == "yes" or row[4] == 1
            else "absent" if value == "no" or row[4] == 0
            else None
        )
        if claim:
            local_records.append({
                "source": row[1], "source_record": row[2],
                "amenity_type": row[3], "claim": claim, "kind": "local",
                "confidence": row[5], "match_distance_m": row[6],
            })

    payload = []
    for status in status_rows:
        amenity = status[0]
        yes_sources = set(json.loads(status[7] or "[]"))
        no_sources = set(json.loads(status[8] or "[]"))
        evidence = [
            item for item in local_records
            if item["amenity_type"] == amenity and (
                (item["claim"] == "present" and item["source"] in yes_sources)
                or (item["claim"] == "absent" and item["source"] in no_sources)
            )
        ]
        if status[9]:
            evidence.append({"source": "OPENSTREETMAP", "claim": "present",
                             "kind": "osm", "explicit": True})
        if status[10]:
            evidence.append({"source": "OPENSTREETMAP", "claim": "absent",
                             "kind": "osm", "explicit": True})

        consensus_claim = status[2] if status[2] in ("yes", "no") else None
        if consensus_claim:
            evidence.append({
                "source": "COMMUNITY_CONSENSUS",
                "claim": "present" if consensus_claim == "yes" else "absent",
                "kind": "community_consensus",
                "count": status[11] if consensus_claim == "yes" else status[12],
            })
        else:
            if status[11]:
                evidence.append({"source": "COMMUNITY", "claim": "present",
                                 "kind": "community", "count": status[11]})
            if status[12]:
                evidence.append({"source": "COMMUNITY", "claim": "absent",
                                 "kind": "community", "count": status[12]})

        payload.append({
            "amenity_type": amenity,
            "derived_status": status[1],
            "consensus_status": status[2],
            "evidence_conflict": bool(status[3]),
            "consensus_conflicts_with_other_evidence": bool(status[4]),
            "rationale": json.loads(status[5]) if status[5] else [],
            "updated_at": status[6],
            "contributing_evidence": evidence,
            "conflict_evidence": evidence if status[3] or status[4] else [],
        })
    return payload


def get_amenity_review_priority(stop_id):
    """Return concise workflow priority when its derived table is available."""
    if not query_db(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='stop_amenity_review_priority'"
    ):
        return []
    return query_db(
        """
        SELECT amenity_type,derived_status,workflow_state,
               rider_exposure_percentile,review_priority_score,priority_tier,
               community_observation_count,observations_needed_for_consensus,
               rationale
        FROM stop_amenity_review_priority WHERE physical_stop_id=?
        ORDER BY review_priority_score DESC,amenity_type
        """,
        (stop_id,),
    )


def serialize_bench_candidate(row):
    return {
        "physical_stop_id": row[0], "candidate_rank": row[1],
        "name": row[2], "state": row[3], "county": row[4],
        "municipality": row[5], "canonical_bench_status": row[6],
        "evidence_strength": row[7],
        "local_negative_sources": json.loads(row[8]) if row[8] else [],
        "osm_negative": bool(row[9]), "community_negative_count": row[10],
        "community_consensus_status": row[11], "opportunity_score": row[12],
        "rider_exposure_percentile": row[13], "review_priority_score": row[14],
        "review_priority_tier": row[15], "clearance_status": row[16],
        "clearance_yes_count": row[17], "clearance_no_count": row[18],
        "recommendation_confidence": row[19],
        "rationale": json.loads(row[20]) if row[20] else [],
        "next_action": row[21], "verification_still_needed": bool(row[22]),
        "engineering_feasibility_established": False, "updated_at": row[23],
    }


def get_bench_candidate(stop_id):
    if not query_db(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='bench_installation_candidates'"
    ):
        return None
    rows = query_db(
        "SELECT * FROM bench_installation_candidates WHERE physical_stop_id=?",
        (stop_id,),
    )
    return serialize_bench_candidate(rows[0]) if rows else None


def serialize_seating_opportunity(row):
    columns = (
        "physical_stop_id", "opportunity_rank", "primary_name", "state", "county",
        "municipality", "bench_status", "shelter_status", "bench_evidence_strength",
        "bench_consensus_status", "adequacy_status", "adequacy_observation_count",
        "adequacy_factors", "clearance_status", "clearance_yes_count",
        "clearance_no_count", "workflow_state", "rider_exposure_percentile",
        "documented_need_index", "strongest_need_signal", "need_signals",
        "rider_benefit_component", "documented_need_component", "priority_score",
        "priority_factors", "rationale", "updated_at",
    )
    item = dict(zip(columns, row))
    for field in ("adequacy_factors", "need_signals", "priority_factors", "rationale"):
        if field in item and isinstance(item[field], str):
            item[field] = json.loads(item[field])
    item["engineering_feasibility_established"] = False
    item["clearance_is_preliminary_observation"] = True
    return item


def get_seating_opportunity(stop_id):
    if not query_db(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='seating_improvement_opportunities'"
    ):
        return None
    rows = query_db(
        "SELECT * FROM seating_improvement_opportunities WHERE physical_stop_id=?",
        (stop_id,),
    )
    if not rows:
        return None
    item = serialize_seating_opportunity(rows[0])
    has_status = query_db(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='stop_amenity_status'"
    )
    status_rows = query_db(
        "SELECT amenity_type,community_observation_count,community_yes_count,"
        "community_no_count FROM stop_amenity_status WHERE physical_stop_id=?",
        (stop_id,),
    ) if has_status else []
    status = {row[0]: row for row in status_rows}
    item["near_consensus"] = any(
        row[1] in (1, 2) and not (row[2] > 0 and row[3] > 0)
        for row in status.values()
    )
    prior = query_db(
        "SELECT COUNT(*),MAX(observed_at) FROM stop_observations "
        "WHERE physical_stop_id=? AND source='community_review'",
        (stop_id,),
    )[0]
    item["prior_observation_count"] = prior[0]
    item["last_observed_at"] = prior[1]
    return item


def stop_is_current(stop_id):
    rows = query_db(
        """
        SELECT physical_stop_id
        FROM stop_gtfs_status
        WHERE physical_stop_id=?
          AND current_gtfs=1
        """,
        (stop_id,)
    )
    return bool(rows)


def inactive_stop_response(stop_id):
    return jsonify(
        {
            "error": "Stop is not current and cannot receive active review work",
            "code": "stop_not_current",
            "stop_id": stop_id,
        }
    ), 409


def retired_stop_payload(stop_id):
    """Describe a historical identity without aliasing it to one successor."""
    tables = query_db("""SELECT name FROM sqlite_master WHERE type='table'
        AND name IN ('physical_stop_identity_state','physical_stop_identity_edges')""")
    if len(tables) != 2:
        return None
    state = query_db("""SELECT identity_status,retired_at
        FROM physical_stop_identity_state WHERE physical_stop_id=?""", (stop_id,))
    if not state or state[0][0] != "retired":
        return None
    successors = [row[0] for row in query_db("""SELECT successor_physical_stop_id
        FROM physical_stop_identity_edges WHERE predecessor_physical_stop_id=?
        ORDER BY successor_physical_stop_id""", (stop_id,))]
    return {
        "stop_id": stop_id,
        "identity_status": "retired",
        "retired_at": state[0][1],
        "message": "This historical physical stop was split into current boarding locations.",
        "successor_stop_ids": successors,
        "successors": [{"stop_id": value, "url": f"/stop/{value}"}
                       for value in successors],
    }






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

    amenity_status = conn.execute(
        """
        SELECT amenity_type, derived_status, consensus_status,
               evidence_conflict, consensus_conflicts_with_other_evidence
        FROM stop_amenity_status
        WHERE physical_stop_id=?
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
        ],

        "amenity_status": {
            row["amenity_type"]: dict(row)
            for row in amenity_status
        }
    }


road_index = None



def get_road_index():

    global road_index

    if road_index is not None:
        return road_index


    try:

        from src.spatial.nearest_road import RoadSpatialIndex

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


    except Exception:

        app.logger.exception("road_centerline_index_build_failed")


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
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

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
        f"&viewpoint={row[1]},{row[2]}"
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

    conn = sqlite3.connect(DATABASE_PATH)

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

        JOIN stop_gtfs_status sgs
            ON sgs.physical_stop_id = ps.id
           AND sgs.current_gtfs = 1

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

    return redirect(url_for("dashboard"))



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

    retired = retired_stop_payload(stop_id)
    if retired:
        return retired, 410

    stop = query_db(
"""
SELECT
    ps.primary_name,
    ps.latitude,
    ps.longitude,
    bs.external_stop_id,
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
        WITH physical_stop_routes AS (

            SELECT DISTINCT
                psm.physical_stop_id,
                r.route_id

            FROM physical_stop_members psm

            JOIN stop_routes sr
                ON psm.bus_stop_id = sr.stop_id

            JOIN routes r
                ON sr.route_id = r.id

            WHERE psm.physical_stop_id = ?

        ),

        latest_ridership AS (

            SELECT
                route_id,
                weekday_boardings,
                period

            FROM ridership_snapshots

            WHERE period = (
                SELECT MAX(period)
                FROM ridership_snapshots
            )

        )

        SELECT
            SUM(lr.weekday_boardings) AS weekday_total,

            COUNT(DISTINCT psr.route_id) AS route_count,

            GROUP_CONCAT(DISTINCT psr.route_id) AS routes,

            (
                SELECT COUNT(*)

                FROM (
                    SELECT 1 AS day
                    UNION ALL SELECT 2
                    UNION ALL SELECT 3
                    UNION ALL SELECT 4
                    UNION ALL SELECT 5
                    UNION ALL SELECT 6
                    UNION ALL SELECT 7
                    UNION ALL SELECT 8
                    UNION ALL SELECT 9
                    UNION ALL SELECT 10
                    UNION ALL SELECT 11
                    UNION ALL SELECT 12
                    UNION ALL SELECT 13
                    UNION ALL SELECT 14
                    UNION ALL SELECT 15
                    UNION ALL SELECT 16
                    UNION ALL SELECT 17
                    UNION ALL SELECT 18
                    UNION ALL SELECT 19
                    UNION ALL SELECT 20
                    UNION ALL SELECT 21
                    UNION ALL SELECT 22
                    UNION ALL SELECT 23
                    UNION ALL SELECT 24
                    UNION ALL SELECT 25
                    UNION ALL SELECT 26
                    UNION ALL SELECT 27
                    UNION ALL SELECT 28
                    UNION ALL SELECT 29
                    UNION ALL SELECT 30
                    UNION ALL SELECT 31
                ) days

                WHERE days.day <= CAST(
                    strftime(
                        '%d',
                        date(
                            lr.period,
                            'start of month',
                            '+1 month',
                            '-1 day'
                        )
                    ) AS INTEGER
                )

                AND strftime(
                    '%w',
                    date(
                        lr.period,
                        'start of month',
                        '+' || (days.day - 1) || ' days'
                    )
                ) BETWEEN '1' AND '5'
            ) AS weekdays_in_period

        FROM physical_stop_routes psr

        JOIN latest_ridership lr
            ON psr.route_id = lr.route_id
        ''',
        (stop_id,)
    )



    rider_exposure = query_db(
        '''
        SELECT
            rider_exposure_percentile

        FROM opportunity_assessments

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )

    rider_exposure_percentile = (
        rider_exposure[0][0] if rider_exposure else None
    )


    ridership_exposure = (
        {
            "weekday_boardings_total":
                round(ridership[0][0])
                if ridership[0][0]
                else 0,

            "average_weekday_boardings":
                round(
                    ridership[0][0]
                    /
                    ridership[0][3]
                )
                if ridership[0][0] and ridership[0][3]
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


    road = get_road_index().nearest_road(
        row[2],
        row[1]
    )


    streetview_display_heading = 0

    if road and road["heading"] is not None:
        streetview_display_heading = road["heading"]


    streetview_url = (
        "https://www.google.com/maps/@?api=1"
        "&map_action=pano"
        f"&viewpoint={row[1]},{row[2]}"
        f"&heading={streetview_display_heading}"
        "&pitch=0"
        "&fov=90"
    )


    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
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
            "external_stop_id": row[3],

            "wmata_rider_tools_url":
                f"https://www.wmata.com/ridertools/stop/{row[3]}"
                if row[3]
                else None,
            "score": row[4],
            "impact": row[5],
            "routes":
                row[6].split(",")
                if row[5]
                else [],
            # Nearest-road camera orientation only. Transit direction is exposed
            # separately by the identity-linked serving_directions payload.
            "streetview_display_heading": streetview_display_heading,
            "streetview_url": streetview_url,


            "wmata_evidence":
                wmata_evidence,


            "ddot_evidence":
                ddot_evidence_payload,

            "ddot_interpretation":
                ddot_interpretation,

            "community_review":
                community_review,

            "amenity_status": list(
                (evidence.get("amenity_status") or {}).values()
            ),

            "recommendations":
                recommendation_payload,

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
    campaign = request.args.get("campaign")

    try:
        campaign = normalize_campaign(campaign) if scenario == "opportunity" else None
    except ValueError as exc:
        return {"error": str(exc)}, 400
    if scenario == "opportunity" and "campaign" not in {
        row[1] for row in query_db("PRAGMA table_info(stop_review_assignments)")
    }:
        return {
            "error": "stop_review_assignments campaign migration is required",
            "code": "review_schema_migration_required",
        }, 503

    stop_id_requested = request.args.get("stop_id")

    requested_stop_id = None

    if stop_id_requested:
        try:
            requested_stop_id = int(stop_id_requested)
        except (TypeError, ValueError):
            return {"error": "valid stop_id required"}, 400

        if not stop_is_current(requested_stop_id):
            return inactive_stop_response(requested_stop_id)

    reviewer_key = session.get(
        "reviewer_key"
    )


    reviewer_id, reviewer_key = (
        get_or_create_reviewer(
            reviewer_key
        )
    )


    session["reviewer_key"] = reviewer_key


    latitude = request.args.get("lat")
    longitude = request.args.get("lon")


    try:
        if stop_id_requested:
            result = assign_stop(reviewer_id, scenario, stop_id=requested_stop_id,
                                 campaign=campaign)
        else:
            result = assign_stop(
                reviewer_id,
                scenario,
                latitude=latitude,
                longitude=longitude,
                campaign=campaign,
            )
    except RuntimeError as exc:
        return {"error": str(exc), "code": "review_schema_migration_required"}, 503


    if not result:
        return {
            "error": "No available review stops"
        }, 404


    assignment_id, stop_id = result


    campaign_query = f"&campaign={campaign}" if campaign else ""
    return redirect(
        f"/review/{stop_id}?assignment_id={assignment_id}&mode={scenario}"
        f"{campaign_query}"
    )


@app.route("/review/<int:stop_id>")
def review_page(stop_id):

    from src.review.render_survey import render_survey

    if not stop_is_current(stop_id):
        return inactive_stop_response(stop_id)

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

            NULL AS wmata_stop_id,
            NULL AS wmata_status,
            NULL AS wmata_heading,
            NULL AS wmata_bench,
            NULL AS wmata_shelter,
            NULL AS wmata_accessible,
            NULL AS match_distance_m,
            NULL AS match_confidence,

            (
                SELECT bs.external_stop_id
                FROM physical_stop_members psm
                JOIN bus_stops bs
                    ON bs.id = psm.bus_stop_id
                WHERE psm.physical_stop_id = p.id
                LIMIT 1
            ) AS external_stop_id

        FROM physical_stops p

        WHERE p.id=?
        """,
        (stop_id,)
    )

    if not stop:
        return {"error": "Stop not found"}, 404

    row = stop[0]


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
            "physical_stop_id": r[0],
            "ddot_id": r[1],
            "api_id": r[2],
            "lifecycle_status": r[3],
            "routes": r[4].split(",") if r[4] else [],
            "route_count": r[5],
            "confidence": r[6],
            "notes": r[7]
        }
        for r in ddot_evidence
    ]


    ddot_interpretation = interpret_ddot_evidence(
        ddot_evidence_payload
    )



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
                round(ridership[0][0] / latest_ridership_weekdays())
                if ridership[0][0] and latest_ridership_weekdays()
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
                round(ridership[0][0] / latest_ridership_weekdays())
                if ridership[0][0] and latest_ridership_weekdays()
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
            rider_exposure_percentile

        FROM opportunity_assessments

        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    rider_exposure_percentile = (
        rider_exposure[0][0] if rider_exposure else None
    )



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
            notes,
            assignment_id,
            review_mode,
            streetview_imagery_month,
            bench_feasible,
            concrete_pad_needed,
            bench_condition,
            rider_comfort_category,
            accessibility_status,
            weather_exposure,
            riders_avoid_facilities
        FROM stop_observations
        WHERE physical_stop_id=?
        AND source='community_review'
        ORDER BY observed_at DESC
        """,
        (stop_id,)
    )


    community_consensus = query_db(
        """
        SELECT
            has_shelter,
            has_bench,
            ada_accessible,
            confidence,
            seating_type_consensus,
            rider_comfort_consensus,
            hostile_design_consensus,
            bench_feasible
        FROM stop_consensus
        WHERE stop_id=?
        """,
        (stop_id,)
    )


    community_consensus_payload = None

    if community_consensus:

        consensus = community_consensus[0]

        required_reviews = 3
        completed_reviews = len(community_reviews)

        confidence = consensus[3]

        if completed_reviews < required_reviews:
            consensus_status = "awaiting_consensus"

        elif confidence is not None and confidence >= 0.75:
            consensus_status = "consensus_reached"

        else:
            consensus_status = "needs_more_agreement"

        community_consensus_payload = {

            "has_shelter":
                consensus[0],

            "has_bench":
                consensus[1],

            "ada_accessible":
                consensus[2],

            "confidence":
                confidence,

            "seating_type":
                consensus[4],

            "rider_comfort":
                consensus[5],

            "hostile_design":
                consensus[6],

            "bench_feasible":
                consensus[7],

            "review_count":
                completed_reviews,

            "required_reviews":
                required_reviews,

            "status":
                consensus_status
        }


    amenity_evidence = get_current_amenity_evidence(stop_id)
    amenity_status = get_current_amenity_status(stop_id)
    serving_directions = get_serving_directions(stop_id)
    serving_headings = [item["heading_degrees"] for item in serving_directions]
    amenity_review_priority = get_amenity_review_priority(stop_id)
    bench_candidate = get_bench_candidate(stop_id)
    seating_opportunity = get_seating_opportunity(stop_id)
    assignment_context = None
    context_scenario = request.args.get("mode")
    context_campaign = request.args.get("campaign")
    assignment_id_arg = request.args.get("assignment_id")
    if assignment_id_arg:
        assignment_rows = query_db(
            "SELECT id, scenario, campaign, status FROM stop_review_assignments "
            "WHERE id=? AND stop_id=?",
            (assignment_id_arg, stop_id),
        )
        if assignment_rows:
            context_scenario = assignment_rows[0][1]
            context_campaign = assignment_rows[0][2]
            assignment_context = {
                "assignment_id": assignment_rows[0][0],
                "assignment_status": assignment_rows[0][3],
            }
    if context_scenario:
        assignment_context = {
            **(assignment_context or {}),
            **build_review_context(
                context_scenario, seating_opportunity, context_campaign
            ),
        }


    improvement_recommendations = query_db(
        """
        SELECT
            id,
            recommendation_type,
            priority,
            reasons,
            confidence,
            evidence,
            created_at
        FROM improvement_recommendations
        WHERE physical_stop_id=?
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            id DESC
        """,
        (stop_id,)
    )


    improvement_recommendations_payload = [
        {
            "id": recommendation[0],

            "type":
                recommendation[1],

            "priority":
                recommendation[2],

            "reasons":
                json.loads(recommendation[3])
                if recommendation[3]
                else [],

            "confidence":
                recommendation[4],

            "evidence":
                json.loads(recommendation[5])
                if recommendation[5]
                else {},

            "created_at":
                recommendation[6]
        }
        for recommendation in improvement_recommendations
    ]


    amenity_evidence_payload = [
        {
            "id": row[0],
            "source": row[1],
            "source_record": row[2],
            "amenity_type": row[3],
            "present": row[4],
            "confidence": row[5],
            "match_distance_m": row[6],
            "notes": row[7],
            "jurisdiction": row[8],
            "value": row[9]
        }
        for row in amenity_evidence
    ]

    amenity_status_payload = build_amenity_status_payload(
        amenity_status, amenity_evidence
    )

    amenity_review_priority_payload = [
        {
            "amenity_type": item[0],
            "derived_status": item[1],
            "workflow_state": item[2],
            "rider_exposure_percentile": item[3],
            "review_priority_score": item[4],
            "priority_tier": item[5],
            "community_observation_count": item[6],
            "observations_needed_for_consensus": item[7],
            "reason": json.loads(item[8]).get("summary") if item[8] else None,
        }
        for item in amenity_review_priority
    ]


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

            "external_stop_id": row[17],

            "wmata_rider_tools_url":
                f"https://www.wmata.com/ridertools/stop/{row[17]}"
                if row[17]
                else None,

            "serving_headings": serving_headings,

            "serving_directions": serving_directions,

            "streetview_url": streetview_url,

            "ddot_evidence":
                ddot_evidence_payload,


            "ddot_interpretation":
                ddot_interpretation,


            "amenity_evidence":
                amenity_evidence_payload,

            "amenity_status":
                amenity_status_payload,

            "amenity_review_priority": amenity_review_priority_payload,

            "seating_improvement_opportunity": seating_opportunity,
            "review_context": assignment_context,
            "bench_installation_candidate": bench_candidate,


            "recommendations":
                improvement_recommendations_payload,


            "community_reviews": {
                "review_count": len(community_reviews),

                "reviews": [
                    {
                        "id": review[0],
                        "date": review[1],
                        "shelter": review[2],
                        "bench": review[3],
                        "notes": review[4].strip() if review[4] else "",
                        "assignment_id": review[5],
                        "review_mode": review[6],
                        "streetview_imagery_month": review[7],
                        "preliminary_clearance": review[8],
                        "concrete_pad_context": review[9],
                        "seating_limitation": review[10],
                        "waiting_environment": review[11],
                        "accessibility_observation": review[12],
                        "weather_exposure": review[13],
                        "riders_avoid_facilities": review[14],
                    }
                    for review in community_reviews
                ]
            },


            "community_consensus":
                community_consensus_payload,


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


@app.route("/bench-candidates")
def bench_candidates():
    if not query_db(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='bench_installation_candidates'"
    ):
        return jsonify({"summary": {}, "candidates": []})
    clauses, params = [], []
    for column in ("state", "county", "municipality", "evidence_strength",
                   "clearance_status", "next_action"):
        value = request.args.get(column)
        if value:
            clauses.append(f"{column}=?")
            params.append(value)
    for column, operator, argument in (
        ("opportunity_score", ">=", "min_opportunity_score"),
        ("rider_exposure_percentile", ">=", "min_rider_exposure_percentile"),
    ):
        value = request.args.get(argument)
        if value is not None:
            try:
                params.append(float(value))
            except ValueError:
                return jsonify({"error": f"{argument} must be numeric"}), 400
            clauses.append(f"{column}{operator}?")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = query_db(
        "SELECT * FROM bench_installation_candidates" + where
        + " ORDER BY candidate_rank", tuple(params)
    )
    candidates = [serialize_bench_candidate(row) for row in rows]
    summary = {
        "bench_candidates": len(candidates),
        "high_ridership_bench_candidates": sum(
            item["rider_exposure_percentile"] >= 90 for item in candidates
        ),
        "needing_clearance_observation": sum(
            item["next_action"] == "collect_clearance_observation"
            for item in candidates
        ),
        "ready_for_planning_review": sum(
            item["next_action"] in
            ("planning_review", "candidate_ready_for_planning")
            for item in candidates
        ),
    }
    return jsonify({"summary": summary, "candidates": candidates})


@app.route("/seating-opportunities")
def seating_opportunities():
    if not query_db(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='seating_improvement_opportunities'"
    ):
        return jsonify({"summary": {}, "opportunities": []})
    clauses, params = [], []
    for column in ("state", "county", "municipality", "bench_status",
                   "adequacy_status", "clearance_status", "workflow_state",
                   "strongest_need_signal"):
        value = request.args.get(column)
        if value:
            clauses.append(f"{column}=?")
            params.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = query_db(
        "SELECT * FROM seating_improvement_opportunities" + where
        + " ORDER BY opportunity_rank", tuple(params)
    )
    opportunities = [serialize_seating_opportunity(row) for row in rows]
    summary = {
        "total_active_stops": len(opportunities),
        "bench_absent": sum(x["bench_status"] in ("likely_no", "confirmed_no") for x in opportunities),
        "bench_likely_present": sum(x["bench_status"] == "likely_yes" for x in opportunities),
        "bench_presence_unknown": sum(x["bench_status"] == "unknown" for x in opportunities),
        "bench_evidence_conflicting": sum(x["bench_status"] == "conflicting" for x in opportunities),
        "bench_present_adequacy_unknown": sum(x["bench_status"] in ("likely_yes", "confirmed_yes") and x["adequacy_status"] == "unknown" for x in opportunities),
        "observed_seating_limitation": sum(x["adequacy_status"] == "limitation_observed" for x in opportunities),
        "documented_need": {
            signal: sum(x["strongest_need_signal"] == signal for x in opportunities)
            for signal in sorted({x["strongest_need_signal"] for x in opportunities})
        },
        "workflow": {state: sum(x["workflow_state"] == state for x in opportunities)
                     for state in ("verify_presence", "assess_adequacy",
                                   "collect_clearance_observation", "planning_review",
                                   "constrained_or_special_review", "no_current_action")},
    }
    return jsonify({"summary": summary, "opportunities": opportunities})





@app.route("/review/<int:stop_id>/assignment")
def review_assignment(stop_id):

    if not stop_is_current(stop_id):
        return inactive_stop_response(stop_id)

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
            SELECT id, reviewer_id, stop_id, scenario, campaign, status

            FROM stop_review_assignments

            WHERE id=?
            """,
            (
                assignment_id,
            )
        )

        if assignment and assignment[0][2] != stop_id:

            return jsonify(
                {
                    "error":
                        "Assignment does not belong to requested stop"
                }
            ), 400


        if assignment and assignment[0][1] != reviewer_id:

            return jsonify(
                {
                    "error":
                        "Assignment does not belong to current reviewer"
                }
            ), 403

    else:

        assignment = query_db(
            """
            SELECT id, reviewer_id, stop_id, scenario, campaign, status

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
        try:
            requested_campaign = (
                normalize_campaign(request.args.get("campaign"))
                if scenario == "opportunity" else None
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        query_db(
            """
            INSERT INTO stop_review_assignments
            (
                stop_id,
                reviewer_id,
                scenario,
                campaign,
                status
            )

            VALUES (?, ?, ?, ?, 'assigned')
            """,
            (
                stop_id,
                reviewer_id,
                scenario,
                requested_campaign,
            )
        )


        assignment = query_db(
            """
            SELECT id, reviewer_id, stop_id, scenario, campaign, status

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


    assignment_reviewer_id = assignment[0][1]

    existing_review = query_db(
        """
        SELECT id
        FROM stop_observations
        WHERE assignment_id=?
        AND source='community_review'
        LIMIT 1
        """,
        (
            assignment[0][0],
        )
    )


    return jsonify(
        {
            "assignment_id":
                assignment[0][0],

            "reviewer_id":
                assignment_reviewer_id,

            "stop_id":
                assignment[0][2],

            "scenario": assignment[0][3],

            "campaign": assignment[0][4],

            "status": assignment[0][5],

            "review_action":
                "update" if existing_review else "new"
        }
    )




@app.route("/stops/<int:stop_id>/community-reviews")
def community_reviews(stop_id):

    observation_columns = {
        row[1] for row in query_db("PRAGMA table_info(stop_observations)")
    }
    review_mode = "review_mode" if "review_mode" in observation_columns else "NULL"
    imagery_month = (
        "streetview_imagery_month"
        if "streetview_imagery_month" in observation_columns else "NULL"
    )
    clearance = "bench_feasible" if "bench_feasible" in observation_columns else "NULL"
    reviews = query_db(
        f"""
        SELECT
            id,
            observed_at,
            shelter_present,
            bench_present,
            notes,
            reviewer_id,
            {review_mode},
            {imagery_month},
            {clearance}
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
                        "notes": row[4],
                        "review_mode": row[6],
                        "streetview_imagery_month": row[7],
                        "preliminary_clearance": row[8],
                    }
                    for row in reviews
                ]
        }
    )


@app.route("/review/submit", methods=["POST"])
def submit_review():

    data = request.json


    # Preserve the original multi-select seating values before
    # converting them to the storage representation used by bench_type.
    seating_values = data.get("seating_type", [])

    if isinstance(seating_values, str):
        seating_values = [seating_values]

    if not isinstance(seating_values, list):
        seating_values = []

    seating_values = [
        str(value).strip()
        for value in seating_values
        if str(value).strip()
    ]

    data["shelter_type"] = (
        data.get("shelter_type")
        or data.get("shelter_protection")
        or ""
    )

    data["bench_type"] = (
        data.get("bench_type")
        or ",".join(seating_values)
    )

    # Normalize seating selections into a conservative bench status.
    #
    # A bench is present only when an actual bench seating type was
    # selected. Individual seats, leaning support, and no seating are
    # explicitly not benches. "Other" and "unknown" cannot establish
    # whether a bench is present.
    bench_seating_types = {
        "full_bench",
        "shelter_bench",
        "non_shelter_bench",
    }

    no_bench_types = {
        "individual_seats",
        "leaning_support",
        "none",
    }

    unknown_types = {
        "other",
        "unknown",
    }

    if any(value in bench_seating_types for value in seating_values):
        data["bench_present"] = "yes"

    elif any(value in no_bench_types for value in seating_values):
        data["bench_present"] = "no"

    elif any(value in unknown_types for value in seating_values):
        data["bench_present"] = "unknown"

    elif data.get("bench_present") in ("yes", "no", "unknown"):
        data["bench_present"] = data.get("bench_present")

    else:
        data["bench_present"] = None

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

    try:
        stop_id = int(stop_id)
    except (TypeError, ValueError):
        return {
            "error": "valid stop_id required"
        }, 400

    # Historical assignments remain stored, but cannot be completed as new
    # active work after the stop becomes non-current.
    if not stop_is_current(stop_id):
        return inactive_stop_response(stop_id)

    required_observation_columns = {
        "assignment_id",
        "weather_exposure",
        "riders_avoid_facilities",
    }
    observation_columns = {
        row[1] for row in query_db("PRAGMA table_info(stop_observations)")
    }
    missing_observation_columns = sorted(
        required_observation_columns - observation_columns
    )
    if missing_observation_columns:
        return {
            "error": "stop_observations schema migration is required",
            "code": "review_schema_migration_required",
            "missing_columns": missing_observation_columns,
        }, 503

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


    assignment = query_db(
        """
        SELECT
            id,
            reviewer_id,
            stop_id,
            status
        FROM stop_review_assignments
        WHERE id=?
        LIMIT 1
        """,
        (
            assignment_id,
        )
    )


    if not assignment:

        return {
            "error":
                "Assignment not found"
        }, 404


    assignment_reviewer_id = assignment[0][1]
    assignment_stop_id = assignment[0][2]
    assignment_status = assignment[0][3]


    if assignment_stop_id != stop_id:

        return {
            "error":
                "Assignment does not belong to submitted stop"
        }, 400


    if assignment_reviewer_id != reviewer_id:

        return {
            "error":
                "Assignment does not belong to current reviewer"
        }, 403


    if assignment_status == "completed":

        return {
            "error":
                "Review already submitted"
        }, 409


    existing_review = query_db(
        """
        SELECT id
        FROM stop_observations
        WHERE assignment_id=?
        AND source='community_review'
        LIMIT 1
        """,
        (assignment_id,)
    )


    reviewer_id = assignment_reviewer_id


    review_action = data.get(
        "review_action",
        "new"
    )


    if existing_review and review_action == "update":

        query_db(
            """
            UPDATE stop_observations
            SET
                observer=?,
                shelter_present=?,
                bench_present=?,
                trash_present=?,
                bench_feasible=?,
                concrete_pad_needed=?,
                ada_clearance_possible=?,
                bench_type=?,
                bench_condition=?,
                shelter_type=?,
                rider_comfort_category=?,
                accessibility_status=?,
                hostile_design=?,
                notes=?,
                confidence=?,
                review_mode=?,
                reviewer_relationship=?,
                rider_activity=?,
                usage_times=?,
                property_owner_outreach=?,
                steward_email=?,
                steward_candidate=?,
                streetview_imagery_month=?,
                weather_exposure=?,
                riders_avoid_facilities=?,
                observed_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data.get("observer", ""),
                data.get("shelter_present"),
                data.get("bench_present"),
                data.get("trash_present"),
                data.get("bench_feasible"),
                data.get("concrete_pad_needed"),
                data.get("ada_clearance_possible"),
                data.get("bench_type", ""),
                data.get("bench_condition", ""),
                data.get("shelter_type", ""),
                data.get("rider_comfort_category", ""),
                data.get("accessibility_status"),
                data.get("hostile_design"),
                data.get("notes"),
                data.get("reviewer_confidence", "unknown"),
                data.get("review_mode"),
                data.get("reviewer_relationship"),
                data.get("rider_activity"),
                data.get("usage_times"),
                data.get("property_owner_outreach", ""),
                data.get("steward_email"),
                data.get("steward_candidate", 0),
                data.get("streetview_imagery_month"),
                data.get("weather_exposure"),
                data.get("riders_avoid_facilities"),
                existing_review[0][0]
            )
        )


    if not (existing_review and review_action == "update"):

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
            hostile_design,
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
            concrete_pad_needed,
            streetview_imagery_month,
            assignment_id,
            weather_exposure,
            riders_avoid_facilities
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """,
        (
            stop_id,
            data.get("observer", ""),
            data.get("shelter_present"),
            data.get("bench_present"),
            data.get("trash_present"),
            data.get("bench_feasible"),
            data.get("ada_clearance_possible"),
            data.get("bench_type", ""),
            data.get("bench_condition", ""),
            data.get("shelter_type", ""),
            data.get("rider_comfort_category", ""),
            data.get("accessibility_status"),
            data.get("hostile_design"),
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
            data.get("concrete_pad_needed"),
            data.get("streetview_imagery_month"),
            assignment_id,
            data.get("weather_exposure"),
            data.get("riders_avoid_facilities")
        )
    )


    # Recalculate community consensus from saved observations.
    consensus = calculate_stop_consensus(stop_id, DATABASE_PATH)

    refresh_conn = sqlite3.connect(DATABASE_PATH)
    try:
        try:
            refresh_after_community_mutation(refresh_conn, stop_id)
        except Exception:
            app.logger.exception(
                "Community evidence saved but derived amenity refresh failed "
                "for stop %s",
                stop_id,
            )
            return {
                "error": "Community evidence was saved, but derived status refresh failed",
                "code": "derived_refresh_failed",
                "stop_id": stop_id,
            }, 500
    finally:
        refresh_conn.close()


    query_db(
        """
        UPDATE stop_review_assignments
        SET status='completed',
            completed_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (assignment_id,)
    )

    app.logger.info(
        "review_completed stop_id=%s assignment_id=%s reviewer_id=%s",
        stop_id, assignment_id, reviewer_id,
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
            daily_route_exposure,
            average_weekday_boardings
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

        "consensus": consensus,

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

    "average_weekday_boardings":
        impact[0][1]
        if impact
        else None,

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

    columns = {row[1] for row in conn.execute("PRAGMA table_info(review_queue)")}
    has_priority = "review_priority_score" in columns
    priority_select = (
        "rq.review_priority_score,rq.priority_amenity,"
        "rq.shelter_review_priority,rq.bench_review_priority,"
        "rq.rider_exposure_percentile,rq.priority_reason"
        if has_priority else
        "NULL review_priority_score,NULL priority_amenity,"
        "NULL shelter_review_priority,NULL bench_review_priority,"
        "NULL rider_exposure_percentile,NULL priority_reason"
    )
    order = "rq.review_priority_score DESC," if has_priority else ""
    rows = conn.execute(
        f"""
        SELECT
            rq.physical_stop_id,
            ps.latitude AS lat,
            ps.longitude AS lon,
            rq.priority_rank,
            rq.opportunity_score,
            rq.location_name,
            rq.review_status,
            rq.consensus_status,
            {priority_select}

        FROM review_queue rq

        JOIN physical_stops ps
            ON ps.id = rq.physical_stop_id

        JOIN stop_gtfs_status sgs
            ON sgs.physical_stop_id = rq.physical_stop_id
           AND sgs.current_gtfs = 1

        WHERE rq.review_status = 'pending'

        ORDER BY
            {order}
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
                    "consensus_status": row["consensus_status"],
                    "review_priority_score": row["review_priority_score"],
                    "priority_amenity": row["priority_amenity"],
                    "shelter_review_priority": row["shelter_review_priority"],
                    "bench_review_priority": row["bench_review_priority"],
                    "rider_exposure_percentile": row["rider_exposure_percentile"],
                    "priority_reason": row["priority_reason"]
                }
                for row in rows
            ]
        }
    )


@app.route("/stops/<int:stop_id>/review-summary")
def stop_review_summary(stop_id):

    evidence = get_stop_evidence_summary(stop_id)

    transit = evidence.get("transit") or {}
    reviews = evidence.get("reviews") or []
    amenity_status = evidence.get("amenity_status") or {}

    reasons = []

    if transit.get("gtfs_bus_stop"):
        reasons.append(
            "Active transit stop confirmed"
        )

    for amenity in ("bench", "shelter"):
        status = (amenity_status.get(amenity) or {}).get("derived_status", "unknown")
        if status in ("likely_yes", "likely_no", "conflicting", "unknown"):
            reasons.append(f"Canonical {amenity} status requires verification: {status}")

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

                "amenity_status": amenity_status,

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

        JOIN stop_gtfs_status sgs
            ON sgs.physical_stop_id = ps.id
           AND sgs.current_gtfs = 1

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

            JOIN stop_gtfs_status sgs
                ON sgs.physical_stop_id = ps.id
               AND sgs.current_gtfs = 1

            JOIN improvement_opportunities io
                ON ps.id = io.physical_stop_id

            JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            JOIN bus_stops bs
                ON psm.bus_stop_id = bs.id

            JOIN stop_routes sr
                ON bs.id = sr.stop_id

            JOIN routes r
                ON sr.route_id = r.id

            LEFT JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            LEFT JOIN stop_consensus ca
                ON ps.id = ca.stop_id

            LEFT JOIN stop_jurisdiction sj
                ON ps.id = sj.stop_id

            WHERE r.route_id = ?

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

            JOIN stop_gtfs_status sgs
                ON sgs.physical_stop_id = ps.id
               AND sgs.current_gtfs = 1

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

    columns = {
        row[1]
        for row in query_db(
            "PRAGMA table_info(stop_improvement_impact)"
        )
    }

    # priority_level is a derived classification populated by
    # scripts/active/generate_priority_levels.py. Before that rebuild has run, the
    # endpoint has no classifications to report; impact_level is not a proxy.
    if "priority_level" not in columns:
        return jsonify(
            {
                "P1": 0,
                "P2": 0,
                "P3": 0,
                "monitor": 0
            }
        )

    rows = query_db(
        """
        SELECT
            priority_level,
            COUNT(*) AS count

        FROM stop_improvement_impact

        JOIN stop_gtfs_status sgs
            ON sgs.physical_stop_id =
               stop_improvement_impact.physical_stop_id
           AND sgs.current_gtfs = 1

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
    ON r.id = sr.route_id

JOIN bus_stops bs
    ON sr.stop_id = bs.id

JOIN physical_stop_members psm
    ON bs.id = psm.bus_stop_id

JOIN physical_stops ps
    ON psm.physical_stop_id = ps.id

JOIN stop_gtfs_status sgs
    ON sgs.physical_stop_id = ps.id
   AND sgs.current_gtfs = 1

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


def _auth_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _reviewer_email_status():
    if app.testing or os.environ.get("REVIEWER_AUTH_DEV_MODE") == "1":
        return {"available": True, "backend": "development"}
    return email_delivery_status(app.config.get("REVIEWER_EMAIL_SENDER"))


@app.route("/api/reviewer/email-auth-health")
def reviewer_email_auth_health():
    status = _reviewer_email_status()
    return {
        "available": status["available"],
        "backend": status.get("backend"),
        "secure_cookie": bool(app.config.get("SESSION_COOKIE_SECURE")),
        "required_configuration": [
            "FLASK_SECRET_KEY", "DMV_BUS_STOPS_DB", "SESSION_COOKIE_SECURE",
            "REVIEWER_EMAIL_BACKEND", "REVIEWER_EMAIL_FROM", "SMTP_HOST",
            "SMTP_PORT", "SMTP_USE_TLS",
        ],
    }


def _send_reviewer_magic_link(email, link, expires_minutes):
    sender = app.config.get("REVIEWER_EMAIL_SENDER")
    if sender:
        sender(email, link, expires_minutes)
        return
    if app.testing or os.environ.get("REVIEWER_AUTH_DEV_MODE") == "1":
        app.extensions.setdefault("reviewer_auth_outbox", []).append(
            (email, link, expires_minutes)
        )
        return
    smtp_sender_from_env()(email, link, expires_minutes)


@app.route("/reviewer/sign-in", methods=["GET", "POST"])
def reviewer_sign_in():
    reviewer_key = session.get("reviewer_key")
    if request.method == "GET":
        csrf = secrets.token_urlsafe(24)
        session["auth_csrf"] = csrf
        return render_template(
            "reviewer_sign_in.html", csrf_token=csrf,
            email_auth_available=_reviewer_email_status()["available"],
        )
    data = request.get_json(silent=True) or request.form
    if not app.testing and data.get("csrf_token") != session.get("auth_csrf"):
        return {"error": "Invalid request token"}, 400
    conn = None
    try:
        email = normalize_email(data.get("email"))
        conn = _auth_db()
        enforce_login_rate_limits(
            conn, email, request.remote_addr, app.secret_key
        )
        owner = conn.execute(
            "SELECT id FROM community_reviewers WHERE email=? "
            "AND email_verified_at IS NOT NULL", (email,)
        ).fetchone()
        if reviewer_key:
            reviewer_id, reviewer_key = get_or_create_reviewer(reviewer_key)
            session["reviewer_key"] = reviewer_key
        elif owner:
            reviewer_id = owner[0]
        else:
            reviewer_id, reviewer_key = get_or_create_reviewer()
            session["reviewer_key"] = reviewer_key
        raw = issue_login_token(conn, reviewer_id, email)
        link = url_for("reviewer_verify", token=raw, _external=True)
        try:
            _send_reviewer_magic_link(email, link, TOKEN_LIFETIME_MINUTES)
        except Exception as exc:
            invalidate_login_token(conn, raw)
            raise RuntimeError("email delivery failed") from exc
        supersede_login_tokens(conn, raw, email)
        conn.close()
    except RateLimitError as exc:
        if conn is not None:
            conn.close()
        response = jsonify({
            "message": "If that address can receive sign-in links, check your email."
        })
        response.status_code = 429
        response.headers["Retry-After"] = str(exc.retry_after)
        return response
    except ValueError as exc:
        if conn is not None:
            conn.close()
        return {"error": str(exc)}, 400
    except (EmailConfigurationError, OSError, RuntimeError):
        if conn is not None:
            conn.close()
        return {"error": "Email sign-in is temporarily unavailable. You can still review anonymously."}, 503
    except sqlite3.DatabaseError:
        if conn is not None:
            conn.close()
        return {"error": "Email sign-in is temporarily unavailable. You can still review anonymously."}, 503
    response = {"message": "If that address can receive sign-in links, check your email."}
    if app.testing or os.environ.get("REVIEWER_AUTH_DEV_MODE") == "1":
        response["magic_link"] = link
    return response


@app.route("/reviewer/verify")
def reviewer_verify():
    token = request.args.get("token", "")
    conn = None
    try:
        conn = _auth_db()
        reviewer_id = consume_login_token(conn, token)
        reviewer = conn.execute(
            "SELECT reviewer_key FROM community_reviewers WHERE id=?", (reviewer_id,)
        ).fetchone()
    except PermissionError as exc:
        return {"error": str(exc), "code": "account_conflict"}, 409
    except ValueError as exc:
        return {"error": str(exc)}, 400
    finally:
        if conn is not None:
            conn.close()
    session.clear()
    session["reviewer_key"] = reviewer[0]
    session["authenticated_reviewer_id"] = reviewer_id
    session["auth_csrf"] = secrets.token_urlsafe(24)
    session.permanent = True
    return redirect("/reviewer/profile")


@app.route("/reviewer/sign-out", methods=["POST"])
def reviewer_sign_out():
    data = request.get_json(silent=True) or request.form
    if data.get("csrf_token") != session.get("auth_csrf"):
        return {"error": "Invalid request token"}, 400
    session.clear()
    return {"success": True}


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
            id, display_name, email, email_verified_at
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
                reviewer[0][1] if reviewer[0][1] else "Community Volunteer",
            "signed_in": session.get("authenticated_reviewer_id") == reviewer[0][0],
            "email": reviewer[0][2]
                if session.get("authenticated_reviewer_id") == reviewer[0][0]
                and reviewer[0][3] else None,
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
        SELECT id, display_name, email, email_verified_at
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
                reviewer[0][1]
                if reviewer and reviewer[0][1]
                else None,
            "signed_in": bool(
                reviewer and session.get("authenticated_reviewer_id") == reviewer[0][0]
            ),
            "email": reviewer[0][2]
                if reviewer and reviewer[0][3]
                and session.get("authenticated_reviewer_id") == reviewer[0][0]
                else None,
            "csrf_token": session.get("auth_csrf")
                if reviewer and session.get("authenticated_reviewer_id") == reviewer[0][0]
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
    table_exists = query_db(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='stop_amenity_status'"
    )
    if not table_exists:
        total = query_db(
            "SELECT COUNT(*) FROM stop_gtfs_status WHERE current_gtfs=1"
        )[0][0]
        return {
            "total": total, "likely_shelter": 0, "likely_bench": 0,
            "no_shelter_evidence": total
        }

    summary = query_db(
        """
        SELECT
            COUNT(DISTINCT physical_stop_id) total,
            SUM(amenity_type='shelter' AND derived_status IN ('confirmed_yes','likely_yes')) likely_shelter,
            SUM(amenity_type='bench' AND derived_status IN ('confirmed_yes','likely_yes')) likely_bench,
            SUM(amenity_type='shelter' AND derived_status='unknown') no_shelter_evidence
        FROM stop_amenity_status
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
    try:
        table_exists = conn.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='stop_amenity_status'
            """
        ).fetchone()
        rows = geography_status_rows(conn) if table_exists else []
        return jsonify(rows)
    finally:
        conn.close()





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


"""Build the canonical, all-active-stop seating opportunity representation."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "src" / "database" / "dmv_bus_stops.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS seating_improvement_opportunities (
    physical_stop_id INTEGER PRIMARY KEY,
    opportunity_rank INTEGER NOT NULL,
    primary_name TEXT,
    state TEXT,
    county TEXT,
    municipality TEXT,
    bench_status TEXT NOT NULL,
    shelter_status TEXT NOT NULL,
    bench_evidence_strength TEXT NOT NULL,
    bench_consensus_status TEXT NOT NULL,
    adequacy_status TEXT NOT NULL,
    adequacy_observation_count INTEGER NOT NULL,
    adequacy_factors TEXT NOT NULL,
    clearance_status TEXT NOT NULL,
    clearance_yes_count INTEGER NOT NULL,
    clearance_no_count INTEGER NOT NULL,
    workflow_state TEXT NOT NULL,
    rider_exposure_percentile REAL NOT NULL,
    documented_need_index REAL NOT NULL,
    strongest_need_signal TEXT NOT NULL,
    need_signals TEXT NOT NULL,
    rider_benefit_component REAL NOT NULL,
    documented_need_component REAL NOT NULL,
    priority_score REAL NOT NULL,
    priority_factors TEXT NOT NULL,
    rationale TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (physical_stop_id) REFERENCES physical_stops(id)
);
CREATE INDEX IF NOT EXISTS idx_seating_opportunity_order
ON seating_improvement_opportunities(priority_score DESC, physical_stop_id);
"""


def observed_seating(bench_present, bench_type):
    seating_types = {
        "full_bench", "shelter_bench", "individual_seats", "leaning_support",
        "non_shelter_bench", "other",
    }
    values = {value.strip() for value in (bench_type or "").split(",")}
    return bench_present == "yes" or bool(values & seating_types)


def classify_adequacy(observations):
    """Keep presence and adequacy separate, while failing closed on adequacy."""
    limitation_values = {"dividers", "small", "leaning", "other"}
    limitations = sum(row[2] in limitation_values for row in observations)
    limitations += sum(row[3] in {"fair", "poor"} for row in observations)
    limitations += sum(row[4] in {"possible_obstruction", "blocked"} for row in observations)
    limitations += sum(row[5] in {"partial", "exposed"} for row in observations)
    limitations += sum(row[6] == "yes" for row in observations)
    explicit_clear = sum(
        observed_seating(row[0], row[1])
        and row[2] == "none" and row[3] == "good" and row[4] == "good"
        and row[5] in (None, "unknown", "protected")
        and row[6] in (None, "unknown", "no")
        for row in observations
    )
    if limitations:
        status = "limitation_observed"
    elif explicit_clear:
        status = "no_limitation_observed"
    else:
        status = "unknown"
    return status, {
        "observations": len(observations),
        "limitation_signals": limitations,
        "explicit_no_limitation_observations": explicit_clear,
    }


def classify_clearance(yes_count, no_count):
    if no_count:
        return "observed_constrained"
    if yes_count:
        return "observed_clear"
    return "unknown"


def classify_workflow(bench_status, adequacy_status, clearance_status):
    if bench_status in ("unknown", "conflicting"):
        return "verify_presence"
    if adequacy_status == "no_limitation_observed" and bench_status in (
        "confirmed_yes", "likely_yes"
    ):
        return "no_current_action"
    if clearance_status == "observed_constrained":
        return "constrained_or_special_review"
    if adequacy_status == "limitation_observed" or bench_status in (
        "confirmed_no", "likely_no"
    ):
        if clearance_status == "observed_clear":
            return "planning_review"
        return "collect_clearance_observation"
    return "assess_adequacy"


def evidence_strength(status):
    return {
        "confirmed_yes": "confirmed", "confirmed_no": "confirmed",
        "likely_yes": "supported", "likely_no": "supported",
        "conflicting": "conflicting", "unknown": "unknown",
    }[status]


def documented_need(bench_status, shelter_status, observations):
    """Return the strongest documented signal; related evidence never stacks."""
    limitation_values = {"dividers", "small", "leaning", "other"}
    signals = {
        "observed_seating_limitation": 90 if any(
            row[2] in limitation_values for row in observations) else 0,
        "poor_comfort_evidence": 75 if any(
            row[3] == "poor" for row in observations) else 0,
        "confirmed_bench_absence": 55 if bench_status == "confirmed_no" else 0,
        "likely_bench_absence": 45 if bench_status == "likely_no" else 0,
        "fair_comfort_evidence": 40 if any(
            row[3] == "fair" for row in observations) else 0,
        "shelter_absence_context": 20 if shelter_status in (
            "confirmed_no", "likely_no") else 0,
    }
    order = tuple(signals)
    strongest = max(order, key=lambda name: (signals[name], -order.index(name)))
    if signals[strongest] == 0:
        strongest = "no_documented_need"
    return max(signals.values()), strongest, signals


def priority(documented_need_index, exposure):
    """Provisional ranking only; never an eligibility or feasibility test."""
    need_component = round(float(documented_need_index) * 0.60, 2)
    rider_component = round(float(exposure or 0) * 0.40, 2)
    return need_component, rider_component, round(need_component + rider_component, 2)


def _observation_columns(conn):
    return {row[1] for row in conn.execute("PRAGMA table_info(stop_observations)")}


def build_opportunities(conn, physical_stop_id=None, recompute_ranks=True):
    existing = {row[1] for row in conn.execute(
        "PRAGMA table_info(seating_improvement_opportunities)"
    )}
    if existing and "documented_need_index" not in existing:
        if physical_stop_id is not None:
            raise RuntimeError(
                "Seating opportunity schema requires a full one-time rebuild "
                "before targeted refresh is available"
            )
        conn.execute("DROP TABLE seating_improvement_opportunities")
    conn.executescript(SCHEMA_SQL)
    conn.row_factory = sqlite3.Row
    where = "" if physical_stop_id is None else "AND g.physical_stop_id=?"
    params = () if physical_stop_id is None else (physical_stop_id,)
    rows = conn.execute(f"""
        SELECT g.physical_stop_id, p.primary_name, j.state, j.county, j.municipality,
          b.derived_status bench_status, b.consensus_status bench_consensus,
          s.derived_status shelter_status,
          COALESCE(oa.rider_exposure_percentile,0) exposure
        FROM stop_gtfs_status g JOIN physical_stops p ON p.id=g.physical_stop_id
        LEFT JOIN stop_jurisdiction j ON j.stop_id=g.physical_stop_id
        JOIN stop_amenity_status b ON b.physical_stop_id=g.physical_stop_id AND b.amenity_type='bench'
        JOIN stop_amenity_status s ON s.physical_stop_id=g.physical_stop_id AND s.amenity_type='shelter'
        LEFT JOIN opportunity_assessments oa ON oa.physical_stop_id=g.physical_stop_id
        WHERE g.current_gtfs=1 {where}
    """, params).fetchall()
    columns = _observation_columns(conn)
    weather = "weather_exposure" if "weather_exposure" in columns else "NULL"
    avoidance = "riders_avoid_facilities" if "riders_avoid_facilities" in columns else "NULL"
    built = []
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        observations = conn.execute(f"""
          SELECT bench_present,bench_type,bench_condition,
                 rider_comfort_category,accessibility_status,
                 {weather},{avoidance}
          FROM stop_observations
          WHERE physical_stop_id=? AND source='community_review'
        """, (row["physical_stop_id"],)).fetchall()
        adequacy_status, adequacy_factors = classify_adequacy(observations)
        yes_count, no_count = conn.execute("""
          SELECT COALESCE(SUM(bench_feasible='yes'),0),
                 COALESCE(SUM(bench_feasible='no'),0)
          FROM stop_observations WHERE physical_stop_id=? AND source='community_review'
        """, (row["physical_stop_id"],)).fetchone()
        clearance = classify_clearance(yes_count, no_count)
        workflow = classify_workflow(row["bench_status"], adequacy_status, clearance)
        need_index, strongest_signal, need_signals = documented_need(
            row["bench_status"], row["shelter_status"], observations
        )
        need_component, rider_component, score = priority(need_index, row["exposure"])
        factors = {
            "documented_need": {"weight": 0.60, "value": need_index,
                                "component": need_component,
                                "strongest_signal": strongest_signal,
                                "signals": need_signals},
            "rider_exposure": {"weight": 0.40, "value": row["exposure"],
                               "component": rider_component,
                               "meaning": "route-based rider exposure, not observed stop-level boardings"},
        }
        rationale = [f"Strongest documented need: {strongest_signal} ({need_index}/100).",
                     f"Existing bench status: {row['bench_status']}.",
                     f"Seating adequacy: {adequacy_status}.",
                     f"Preliminary visual clearance: {clearance}; engineering feasibility is not established.",
                     f"Next action: {workflow}."]
        built.append((row, adequacy_status, adequacy_factors, clearance,
                      yes_count, no_count, workflow, need_index, strongest_signal,
                      need_signals, need_component, rider_component, score,
                      factors, rationale, now))
    with conn:
        if physical_stop_id is None:
            conn.execute("DELETE FROM seating_improvement_opportunities")
        else:
            conn.execute("DELETE FROM seating_improvement_opportunities WHERE physical_stop_id=?", params)
        for item in built:
            (row, adequacy_status, af, clearance, yc, nc, workflow, need_index,
             strongest_signal, need_signals, need_component, rider_component,
             score, factors, rationale, now) = item
            conn.execute("""INSERT INTO seating_improvement_opportunities VALUES
              (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                row["physical_stop_id"], 0, row["primary_name"], row["state"], row["county"],
                row["municipality"], row["bench_status"], row["shelter_status"],
                evidence_strength(row["bench_status"]), row["bench_consensus"], adequacy_status,
                af["observations"], json.dumps(af, sort_keys=True),
                clearance, yc, nc, workflow, row["exposure"], need_index,
                strongest_signal, json.dumps(need_signals, sort_keys=True),
                rider_component, need_component, score,
                json.dumps(factors, sort_keys=True), json.dumps(rationale), now))
        if recompute_ranks:
            ranked = conn.execute("SELECT physical_stop_id FROM seating_improvement_opportunities ORDER BY priority_score DESC, rider_exposure_percentile DESC, physical_stop_id").fetchall()
            conn.executemany("UPDATE seating_improvement_opportunities SET opportunity_rank=? WHERE physical_stop_id=?",
                             ((rank, row[0]) for rank, row in enumerate(ranked, 1)))
    return len(built)


def generate_opportunities(database_path=None):
    with sqlite3.connect(database_path or DATABASE_PATH) as conn:
        count = build_opportunities(conn)
    print(f"Created {count:,} seating improvement opportunities")
    return count


if __name__ == "__main__":
    generate_opportunities()

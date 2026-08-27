#!/usr/bin/env python3
"""Read-only audit of human-reviewed OSM bench/shelter contribution candidates."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.amenities.status_synthesis import (  # noqa: E402
    CONSENSUS_CONFIDENCE_THRESHOLD,
    CONSENSUS_REVIEW_THRESHOLD,
)
from src.processing.serving_directions import load_member_directions  # noqa: E402


DEFAULT_DB = REPO_ROOT / "src" / "database" / "dmv_bus_stops.db"
ATTRIBUTION_VERSION = "physical-stop-v2-cutover-1"
AMENITIES = ("bench", "shelter")
EXACT_METHODS = {"exact_member", "exact_source_record"}


def connect_read_only(path):
    resolved = Path(path).resolve()
    return sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro", uri=True)


def parse_tags(value):
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def osm_refs(tags):
    result = set()
    for key in ("ref:wmata", "ref"):
        for item in str(tags.get(key, "")).replace(",", ";").split(";"):
            if item.strip():
                result.add(item.strip())
    return result


def normalized_yes_no(value):
    value = str(value or "").strip().lower()
    return value if value in {"yes", "no"} else None


def parsed_date(value):
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def effective_observation_date(row):
    if row["review_mode"] != "in_person" and row["streetview_imagery_month"]:
        return parsed_date(f"{row['streetview_imagery_month']}-01")
    return parsed_date(row["observed_at"])


def current_osm_date(tags, amenity, snapshot_date):
    values = [
        tags.get(f"check_date:{amenity}"),
        tags.get(f"{amenity}:check_date"),
        tags.get("check_date"),
        snapshot_date,
    ]
    dates = [parsed_date(value) for value in values]
    return max((value for value in dates if value), default=None)


def table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def load_attributions(conn):
    if not table_exists(conn, "physical_stop_evidence_attribution"):
        return {}
    rows = conn.execute(
        """
        SELECT evidence_row_id, physical_stop_id, attribution_method,
               attribution_version, provenance_json, attributed_at
        FROM physical_stop_evidence_attribution
        WHERE evidence_table='stop_osm_evidence'
        ORDER BY evidence_row_id,
                 CASE WHEN attribution_version=? THEN 0 ELSE 1 END,
                 datetime(attributed_at) DESC, attribution_version DESC
        """,
        (ATTRIBUTION_VERSION,),
    )
    result = {}
    for row in rows:
        result.setdefault(row[0], row[1:])
    return result


def load_objects(conn):
    if not table_exists(conn, "osm_features"):
        return {}
    values = defaultdict(set)
    for feature_id, osm_id, osm_type in conn.execute(
        "SELECT id, osm_id, osm_type FROM osm_features WHERE osm_id IS NOT NULL"
    ):
        if osm_type:
            values[str(feature_id)].add((str(osm_type).lower(), str(osm_id)))
    return values


def load_observations(conn):
    rows = defaultdict(list)
    conn.row_factory = sqlite3.Row
    for row in conn.execute(
        """
        SELECT id, physical_stop_id, shelter_present, bench_present,
               observed_at, review_mode, streetview_imagery_month
        FROM stop_observations
        WHERE source='community_review'
        ORDER BY physical_stop_id, datetime(observed_at), id
        """
    ):
        rows[row["physical_stop_id"]].append(row)
    conn.row_factory = None
    return rows


def community_record(stop_id, amenity, observations, consensus):
    field = f"{amenity}_present"
    usable = [
        row for row in observations.get(stop_id, [])
        if normalized_yes_no(row[field])
    ]
    consensus_row = consensus.get(stop_id)
    consensus_value = None if not consensus_row else consensus_row[amenity]
    full_consensus = bool(
        consensus_row
        and len(usable) >= CONSENSUS_REVIEW_THRESHOLD
        and consensus_row["confidence"] is not None
        and consensus_row["confidence"] >= CONSENSUS_CONFIDENCE_THRESHOLD
        and consensus_value in (0, 1)
    )
    if full_consensus:
        value = "yes" if consensus_value == 1 else "no"
        support = [row for row in usable if normalized_yes_no(row[field]) == value]
        reason = "reached community consensus"
        status = f"confirmed_{value}"
    else:
        direct = [row for row in usable if row["review_mode"] == "in_person"]
        if not direct:
            return None
        latest = max(direct, key=lambda row: (
            effective_observation_date(row) or datetime.min.date(), row["id"]
        ))
        value = normalized_yes_no(latest[field])
        support = [latest]
        reason = "latest direct in-person community observation"
        status = "direct_observation"
    dates = [effective_observation_date(row) for row in support]
    return {
        "value": value,
        "observation_ids": [row["id"] for row in support],
        "observation_dates": [value.isoformat() for value in dates if value],
        "latest_date": max((value for value in dates if value), default=None),
        "consensus_status": status,
        "reason": reason,
    }


def direction_payload(direction_rows):
    values = []
    for member_id in sorted(direction_rows):
        for item in direction_rows[member_id]:
            degrees = round(float(item["heading_degrees"]), 1)
            if degrees not in values:
                values.append(degrees)
    return values


def audit(conn):
    conn.row_factory = None
    active_rows = list(conn.execute(
        """
        SELECT s.physical_stop_id, p.primary_name, p.state, p.county,
               p.municipality, p.dc_ward,
               COALESCE(i.identity_status, 'current')
        FROM stop_gtfs_status s
        JOIN physical_stops p ON p.id=s.physical_stop_id
        LEFT JOIN physical_stop_identity_state i ON i.physical_stop_id=p.id
        WHERE s.current_gtfs=1
        ORDER BY s.physical_stop_id
        """
    ))
    active = {row[0] for row in active_rows}
    details = {
        row[0]: {
            "name": row[1],
            "geography": {
                "state": row[2], "county": row[3], "municipality": row[4],
                "dc_ward": row[5],
            },
            "identity_status": row[6],
        }
        for row in active_rows
    }
    external = defaultdict(set)
    reverse_external = defaultdict(set)
    for stop_id, source_id in conn.execute(
        """
        SELECT pm.physical_stop_id, b.external_stop_id
        FROM physical_stop_members pm JOIN bus_stops b ON b.id=pm.bus_stop_id
        WHERE b.external_stop_id IS NOT NULL
        """
    ):
        source_id = str(source_id).strip()
        external[stop_id].add(source_id)
        if stop_id in active:
            reverse_external[source_id].add(stop_id)

    attributions = load_attributions(conn)
    objects = load_objects(conn)
    exact_by_stop = defaultdict(list)
    spatial_by_stop = defaultdict(list)
    excluded_evidence = Counter()
    osm_rows = list(conn.execute(
        """SELECT id,stop_id,osm_feature_id,osm_tags,osm_snapshot_date,
                  osm_source_file FROM stop_osm_evidence ORDER BY id"""
    ))
    for row in osm_rows:
        row_id, legacy_stop_id, feature_id, raw_tags, snapshot_date, source_file = row
        tags = parse_tags(raw_tags)
        refs = osm_refs(tags)
        attribution = attributions.get(row_id)
        matched_stop = None
        method = None
        provenance = {}
        if attribution:
            attributed_stop, method, version, raw_provenance, _ = attribution
            provenance = parse_tags(raw_provenance)
            if method == "unresolved":
                excluded_evidence["unresolved_v2_attribution"] += 1
                continue
            if attributed_stop in active:
                matched_stop = attributed_stop
            elif method in EXACT_METHODS:
                excluded_evidence["attributed_to_non_active_identity"] += 1
                continue
        if matched_stop is None and attribution is None:
            ref_stops = {stop for ref in refs for stop in reverse_external.get(ref, set())}
            if len(ref_stops) == 1:
                matched_stop = next(iter(ref_stops))
                method = "exact_member_ref"
                provenance = {"matched_refs": sorted(refs & external[matched_stop])}
            elif len(ref_stops) > 1:
                excluded_evidence["ambiguous_exact_reference"] += 1
                continue
            elif legacy_stop_id in active:
                matched_stop = legacy_stop_id
                method = "legacy_spatial_association"
        if matched_stop is None:
            excluded_evidence["unresolved_or_no_active_match"] += 1
            continue
        item = {
            "evidence_id": row_id,
            "osm_feature_id": str(feature_id) if feature_id is not None else None,
            "tags": tags,
            "snapshot_date": snapshot_date,
            "source_file": source_file,
            "match_method": method,
            "match_provenance": provenance,
            "attribution_version": attribution[2] if attribution else None,
        }
        if method in EXACT_METHODS or method == "exact_member_ref":
            exact_by_stop[matched_stop].append(item)
        else:
            spatial_by_stop[matched_stop].append(item)

    coverage = Counter()
    for stop_id in active:
        if exact_by_stop[stop_id]:
            coverage["exact_identity_matched"] += 1
        elif spatial_by_stop[stop_id]:
            coverage["spatial_only"] += 1
        else:
            coverage["unresolved_or_no_match"] += 1

    observations = load_observations(conn)
    consensus = {}
    if table_exists(conn, "stop_consensus"):
        for stop_id, has_bench, has_shelter, confidence in conn.execute(
            "SELECT stop_id,has_bench,has_shelter,confidence FROM stop_consensus"
        ):
            consensus[stop_id] = {
                "bench": has_bench, "shelter": has_shelter,
                "confidence": confidence,
            }
    directions = load_member_directions(conn)
    classifications = Counter()
    candidate_exclusions = Counter()
    candidates = []
    provenance_gaps = Counter()
    seen_objects = defaultdict(set)
    for stop_id, items in exact_by_stop.items():
        for item in items:
            seen_objects[item["osm_feature_id"]].add(stop_id)
    for stop_id in sorted(exact_by_stop):
        stop = details[stop_id]
        for item in exact_by_stop[stop_id]:
            feature_id = item["osm_feature_id"]
            object_matches = objects.get(feature_id, set())
            object_type, object_id = (
                next(iter(object_matches)) if len(object_matches) == 1
                else (None, None)
            )
            base_warnings = []
            blocked_reason = None
            if stop["identity_status"] == "manual_exception":
                blocked_reason = "manual-exception identity"
            elif len(seen_objects[feature_id]) > 1:
                blocked_reason = "OSM object maps to multiple current sibling identities"
            elif not feature_id:
                blocked_reason = "missing OSM feature reference"
                provenance_gaps["missing_osm_object_id"] += 1
            elif not object_type:
                blocked_reason = "missing or ambiguous OSM object type"
                provenance_gaps["missing_or_ambiguous_osm_object_type"] += 1
            if not item["snapshot_date"]:
                base_warnings.append(
                    "OSM snapshot date is unavailable; verify current tags in OSM before editing."
                )
                provenance_gaps["missing_osm_snapshot_date"] += 1
            if not item["source_file"]:
                provenance_gaps["missing_osm_source_file"] += 1
            for amenity in AMENITIES:
                record = community_record(stop_id, amenity, observations, consensus)
                osm_value = normalized_yes_no(item["tags"].get(amenity))
                if blocked_reason:
                    classifications[f"{amenity}:insufficient_confidence_no_action"] += 1
                    candidate_exclusions[blocked_reason] += 1
                    continue
                if not record:
                    classifications[f"{amenity}:insufficient_confidence_no_action"] += 1
                    candidate_exclusions["no strong community observation or consensus"] += 1
                    continue
                osm_date = current_osm_date(
                    item["tags"], amenity, item["snapshot_date"]
                )
                if osm_date and (
                    not record["latest_date"] or record["latest_date"] <= osm_date
                ):
                    classifications[f"{amenity}:insufficient_confidence_no_action"] += 1
                    candidate_exclusions[
                        "community evidence is not newer than dated OSM evidence"
                    ] += 1
                    continue
                desired = record["value"]
                if osm_value == desired:
                    classifications[f"{amenity}:already_aligned_no_action"] += 1
                    continue
                if osm_value is None and amenity in item["tags"]:
                    classifications[f"{amenity}:insufficient_confidence_no_action"] += 1
                    candidate_exclusions["OSM amenity tag has unsupported value"] += 1
                    continue
                if osm_value is None and desired == "yes":
                    change_type = f"osm_missing_{amenity}_community_confirms_present"
                elif osm_value == "no" and desired == "yes":
                    change_type = f"osm_says_{amenity}_no_community_confirms_present"
                elif osm_value == "yes" and desired == "no":
                    change_type = f"osm_says_{amenity}_yes_community_confirms_absent"
                else:
                    classifications[f"{amenity}:insufficient_confidence_no_action"] += 1
                    candidate_exclusions["missing OSM tag does not support proposed absence"] += 1
                    continue
                classifications[f"{amenity}:{change_type}"] += 1
                candidates.append({
                    "physical_stop_id": stop_id,
                    "current_stop_name": stop["name"],
                    "osm_object_type": object_type,
                    "osm_object_id": object_id,
                    "current_osm_tags": item["tags"],
                    "proposed_tag_change": {amenity: desired},
                    "change_type": change_type,
                    "supporting_observation_ids": record["observation_ids"],
                    "supporting_observation_dates": record["observation_dates"],
                    "consensus_status": record["consensus_status"],
                    "serving_direction_degrees": direction_payload(
                        directions.get(stop_id, {})
                    ),
                    "geography": stop["geography"],
                    "exact_match_provenance": {
                        "method": item["match_method"],
                        "version": item["attribution_version"],
                        "details": item["match_provenance"],
                        "evidence_row_id": item["evidence_id"],
                    },
                    "reason_for_eligibility": record["reason"],
                    "review_warning": " ".join(base_warnings) or None,
                })

    tag_inventory = {key: Counter() for key in (
        "bench", "shelter", "public_transport", "highway",
        "public_transport_semantics",
    )}
    for items in exact_by_stop.values():
        for item in items:
            tags = item["tags"]
            for key in ("bench", "shelter", "public_transport", "highway"):
                tag_inventory[key][str(tags.get(key, "<missing>"))] += 1
            semantics = []
            if tags.get("public_transport") in {"platform", "stop_position"}:
                semantics.append(str(tags["public_transport"]))
            if tags.get("highway") == "bus_stop":
                semantics.append("highway=bus_stop")
            tag_inventory["public_transport_semantics"][
                "+".join(semantics) or "other/unspecified"
            ] += 1

    recommendation = (
        "READY FOR HUMAN-REVIEWED OSM EXPORT"
        if candidates and not provenance_gaps.get("missing_or_ambiguous_osm_object_type")
        else "NEEDS MORE PROVENANCE WORK"
    )
    return {
        "read_only": True,
        "active_stop_count": len(active),
        "coverage": dict(coverage),
        "coverage_examples": {
            "exact_identity_matched": [
                {
                    "physical_stop_id": stop_id,
                    "current_stop_name": details[stop_id]["name"],
                    "osm_evidence_row_ids": [
                        item["evidence_id"] for item in exact_by_stop[stop_id]
                    ],
                    "match_methods": sorted({
                        item["match_method"] for item in exact_by_stop[stop_id]
                    }),
                }
                for stop_id in sorted(exact_by_stop)[:5]
            ],
            "spatial_only": [
                {
                    "physical_stop_id": stop_id,
                    "current_stop_name": details[stop_id]["name"],
                    "osm_evidence_row_ids": [
                        item["evidence_id"] for item in spatial_by_stop[stop_id]
                    ],
                }
                for stop_id in sorted(
                    stop_id for stop_id in active
                    if not exact_by_stop[stop_id] and spatial_by_stop[stop_id]
                )[:5]
            ],
            "unresolved_or_no_match": [
                {
                    "physical_stop_id": stop_id,
                    "current_stop_name": details[stop_id]["name"],
                }
                for stop_id in sorted(
                    stop_id for stop_id in active
                    if not exact_by_stop[stop_id] and not spatial_by_stop[stop_id]
                )[:5]
            ],
        },
        "exact_osm_evidence_row_count": sum(map(len, exact_by_stop.values())),
        "tag_inventory": {
            key: dict(sorted(value.items())) for key, value in tag_inventory.items()
        },
        "candidate_count": len(candidates),
        "classifications": dict(sorted(classifications.items())),
        "excluded_evidence": dict(sorted(excluded_evidence.items())),
        "candidate_exclusions": dict(sorted(candidate_exclusions.items())),
        "provenance_gaps": dict(sorted(provenance_gaps.items())),
        "recommendation": recommendation,
        "candidates": candidates,
    }


def write_output(path, result):
    target = Path(path)
    if target.suffix.lower() == ".json":
        target.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        return
    if target.suffix.lower() != ".csv":
        raise ValueError("--out must end in .json or .csv")
    fields = [
        "physical_stop_id", "current_stop_name", "osm_object_type",
        "osm_object_id", "change_type", "current_osm_tags",
        "proposed_tag_change", "supporting_observation_ids",
        "supporting_observation_dates", "consensus_status",
        "serving_direction_degrees", "geography", "exact_match_provenance",
        "reason_for_eligibility", "review_warning",
    ]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for candidate in result["candidates"]:
            writer.writerow({
                key: json.dumps(candidate[key], sort_keys=True)
                if isinstance(candidate[key], (dict, list)) else candidate[key]
                for key in fields
            })


def print_summary(result):
    print(f"Active stops: {result['active_stop_count']}")
    for key, value in result["coverage"].items():
        print(f"{key}: {value}")
    print(f"Exact OSM evidence rows: {result['exact_osm_evidence_row_count']}")
    print(f"Human-review candidates: {result['candidate_count']}")
    for key, value in result["classifications"].items():
        print(f"{key}: {value}")
    print("Relevant tags on exact-match evidence rows:")
    for key, values in result["tag_inventory"].items():
        print(f"  {key}: {json.dumps(values, sort_keys=True)}")
    print(f"Excluded evidence: {json.dumps(result['excluded_evidence'], sort_keys=True)}")
    print(f"Candidate exclusions: {json.dumps(result['candidate_exclusions'], sort_keys=True)}")
    print(f"Coverage examples: {json.dumps(result['coverage_examples'], sort_keys=True)}")
    print(f"Provenance gaps: {json.dumps(result['provenance_gaps'], sort_keys=True)}")
    print(f"Recommendation: {result['recommendation']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", default=os.environ.get("DMV_BUS_STOPS_DB", str(DEFAULT_DB)),
        help="SQLite database path (opened read-only)",
    )
    parser.add_argument("--summary", action="store_true", help="print summary")
    parser.add_argument("--out", help="optional .json or .csv candidate export")
    args = parser.parse_args(argv)
    conn = connect_read_only(args.db)
    try:
        result = audit(conn)
    finally:
        conn.close()
    if args.out:
        write_output(args.out, result)
    if args.summary or not args.out:
        print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

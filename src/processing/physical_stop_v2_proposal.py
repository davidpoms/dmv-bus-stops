"""Deterministic Physical Stop Identity V2 proposal generator.

This module is read-only. It creates a review/migration proposal but never allocates
or mutates persistent physical-stop identities.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict

from src.processing.heading_audit import distance_m, maximum_heading_separation
from src.processing.physical_stop_identity_v2 import MANUAL_EXCEPTIONS
from src.processing.serving_directions import load_member_directions


PROPOSAL_VERSION = "physical-stop-v2-proposal-1"
EXPECTED_PARENT_COUNT = 384
EXPECTED_CHILD_COUNT = 791
ORDINARY_HEADING_THRESHOLD = 160
REVIEWED_ORDINARY_ADDITIONS = frozenset({82, 2048, 3021})
CONTAMINATION_REFERENCE_CASES = frozenset({
    506, 658, 1437, 1917, 2340, 2451, 3313, 3752, 3802, 4088, 4563,
})

BAY_PATTERN = re.compile(r"\b(?:bus\s+)?(?:bay|platform)\s*#?([A-Z0-9]+)\b", re.I)
FACILITY_PATTERN = re.compile(
    r"\b(station|terminal|bay|platform|loop|transit center|metro|garage|transfer center)\b",
    re.I,
)


class ProposalDriftError(RuntimeError):
    pass


def canonical_json(manifest):
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def manifest_sha256(manifest):
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest().upper()


def _bay_label(name):
    match = BAY_PATTERN.search(name or "")
    return match.group(1).upper() if match else None


def _specific_name(members):
    candidates = {(member["name"] or "").strip() for member in members}
    candidates.discard("")
    return sorted(candidates, key=lambda value: (-len(value), value.casefold(), value))[0] if candidates else None


def _child(members, directions, routes):
    ordered = sorted(members, key=lambda item: item["bus_stop_id"])
    member_ids = [item["bus_stop_id"] for item in ordered]
    child_directions = [direction for member_id in member_ids
                        for direction in directions.get(member_id, [])]
    eligible_gtfs = sorted({item["gtfs_stop_id"] for item in child_directions})
    return {
        "member_bus_stop_ids": member_ids,
        "external_source_ids": [item["external_stop_id"] for item in ordered],
        "eligible_gtfs_stop_ids": eligible_gtfs,
        "source_names": [item["name"] for item in ordered],
        "proposed_name": _specific_name(ordered),
        "proposed_coordinates": [
            sum(item["latitude"] for item in ordered) / len(ordered),
            sum(item["longitude"] for item in ordered) / len(ordered),
        ],
        "serving_headings": sorted({item["heading_degrees"] for item in child_directions}),
        "routes": sorted({route for member_id in member_ids for route in routes.get(member_id, ())}),
        "current_source_members": [item["bus_stop_id"] for item in ordered if item["current_source"]],
        "current_gtfs_expected": any(item["current_source"] for item in ordered),
    }


def _same_exact_boarding_identity(first_id, second_id, directions):
    first = {item["gtfs_stop_id"] for item in directions.get(first_id, [])}
    second = {item["gtfs_stop_id"] for item in directions.get(second_id, [])}
    return bool(first & second)


def generate_manifest(conn, *, validate=False):
    required = {"physical_stops", "physical_stop_members", "bus_stops",
                "gtfs_stop_map", "stop_wmata_evidence", "stop_routes", "routes",
                "stop_gtfs_status"}
    present = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    missing = sorted(required - present)
    if missing:
        raise ProposalDriftError(f"missing proposal input tables: {missing}")

    directions_by_stop = load_member_directions(conn)
    routes = defaultdict(set)
    for member_id, route_id in conn.execute("""SELECT sr.stop_id,r.route_id
        FROM stop_routes sr JOIN routes r ON r.id=sr.route_id
        ORDER BY sr.stop_id,r.route_id"""):
        routes[member_id].add(str(route_id))

    current_members = {row[0] for row in conn.execute(
        "SELECT DISTINCT bus_stop_id FROM gtfs_stop_map"
    )}
    groups = defaultdict(list)
    parent_context = {}
    for row in conn.execute("""
        SELECT ps.id,ps.primary_name,ps.latitude,ps.longitude,
               COALESCE(s.current_gtfs,0),pm.bus_stop_id,b.external_stop_id,
               b.stop_name,b.latitude,b.longitude
        FROM physical_stops ps
        JOIN physical_stop_members pm ON pm.physical_stop_id=ps.id
        JOIN bus_stops b ON b.id=pm.bus_stop_id
        LEFT JOIN stop_gtfs_status s ON s.physical_stop_id=ps.id
        ORDER BY ps.id,pm.bus_stop_id"""):
        (parent_id, parent_name, parent_lat, parent_lon, current, member_id,
         external_id, name, latitude, longitude) = row
        parent_context[parent_id] = (parent_name, parent_lat, parent_lon, bool(current))
        groups[parent_id].append({
            "bus_stop_id": member_id, "external_stop_id": str(external_id),
            "name": name, "latitude": latitude, "longitude": longitude,
            "bay_label": _bay_label(name), "current_source": member_id in current_members,
        })

    parents = []
    for parent_id in sorted(groups):
        if parent_id in MANUAL_EXCEPTIONS or parent_id in CONTAMINATION_REFERENCE_CASES:
            continue
        members = groups[parent_id]
        directions = directions_by_stop.get(parent_id, {})
        labels = sorted({item["bay_label"] for item in members if item["bay_label"]})
        facility = len(labels) > 1
        facility_context = any(FACILITY_PATTERN.search(item["name"] or "") for item in members)
        headings = [item["heading_degrees"] for values in directions.values() for item in values]
        opposed = maximum_heading_separation(headings) >= ORDINARY_HEADING_THRESHOLD
        shared_exact = len(members) == 2 and _same_exact_boarding_identity(
            members[0]["bus_stop_id"], members[1]["bus_stop_id"], directions)
        reviewed_addition = parent_id in REVIEWED_ORDINARY_ADDITIONS
        ordinary = (len(members) == 2 and not facility_context and opposed and not shared_exact)
        if not facility and not ordinary and not reviewed_addition:
            continue

        if facility:
            buckets = defaultdict(list)
            for member in members:
                buckets[member["bay_label"] or f'MEMBER-{member["bus_stop_id"]}'].append(member)
            child_members = [buckets[key] for key in sorted(buckets)]
            classification = "facility_bay_split"
            reason_flags = ["distinct_named_bays"]
        else:
            child_members = [[member] for member in members]
            classification = "ordinary_curb_split"
            reason_flags = (["reviewed_same_boarding_mapping_correction"] if reviewed_addition
                            else ["exact_member_headings_opposed_at_least_160"])
        if len(child_members) < 2:
            continue
        parent_name, parent_lat, parent_lon, current = parent_context[parent_id]
        proposed = [_child(child_members_value, directions, routes)
                    for child_members_value in child_members]
        parents.append({
            "predecessor_physical_stop_id": parent_id,
            "classification": classification,
            "reason_flags": reason_flags,
            "old_name": parent_name,
            "old_coordinates": [parent_lat, parent_lon],
            "members": [{
                "bus_stop_id": member["bus_stop_id"],
                "external_source_id": member["external_stop_id"],
                "source_name": member["name"],
                "coordinates": [member["latitude"], member["longitude"]],
                "eligible_directions": directions.get(member["bus_stop_id"], []),
            } for member in members],
            "proposed_children": proposed,
        })

    manifest = {
        "proposal_version": PROPOSAL_VERSION,
        "generated_from": {
            "required_tables": sorted(required),
            "ordinary_heading_threshold_degrees": ORDINARY_HEADING_THRESHOLD,
            "identity_precedence": "exact_source_then_uncontested_coordinate_fallback",
        },
        "automatic_parent_count": len(parents),
        "child_group_count": sum(len(parent["proposed_children"]) for parent in parents),
        "manual_exceptions": sorted(MANUAL_EXCEPTIONS),
        "parents": parents,
    }
    if validate:
        validate_manifest(manifest)
    return manifest


def validate_manifest(manifest):
    parent_count = manifest["automatic_parent_count"]
    child_count = manifest["child_group_count"]
    if parent_count != EXPECTED_PARENT_COUNT or child_count != EXPECTED_CHILD_COUNT:
        raise ProposalDriftError(
            f"proposal cardinality drift: parents {parent_count}/{EXPECTED_PARENT_COUNT}; "
            f"children {child_count}/{EXPECTED_CHILD_COUNT}"
        )
    if manifest["manual_exceptions"] != sorted(MANUAL_EXCEPTIONS):
        raise ProposalDriftError("manual exception set drift")
    for parent in manifest["parents"]:
        original = sorted(member["bus_stop_id"] for member in parent["members"])
        proposed = sorted(member for child in parent["proposed_children"]
                          for member in child["member_bus_stop_ids"])
        if original != proposed or len(proposed) != len(set(proposed)):
            raise ProposalDriftError(
                f"member partition drift at {parent['predecessor_physical_stop_id']}"
            )
    return True


def semantic_grouping(manifest):
    return {parent["predecessor_physical_stop_id"]: tuple(sorted(
        tuple(sorted(child["member_bus_stop_ids"])) for child in parent["proposed_children"]
    )) for parent in manifest["parents"]}

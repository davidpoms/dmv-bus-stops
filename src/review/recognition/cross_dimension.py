"""Pure adjudication of five unapproved evidence packages; never certification."""

from copy import deepcopy
from itertools import combinations

from .rules import canonical, digest


FORMAT = "geography-cross-dimension-adjudication-v1"
DIMENSIONS = ("dc_ward", "dc_anc", "county", "state", "census_place")


def _ward(b):
    return (b["source_snapshot"], b["source_gtfs_status_rows"],
            b["identity_history"]["all_events"], b["identity_history"]["all_edges"],
            b["identity_history"]["represented_member_states"])


def _anc(b):
    h = b["identity_history"]
    return b["source_snapshot"], b["gtfs_status_rows"], h["events"], h["edges"], h["states"]


def _county(b):
    h = b["identity_history"]
    return b["snapshot"], b["gtfs_status_rows"], h["events"], h["edges"], h["states"]


def _state(b):
    h = b["identity_history"]
    return b["snapshot"], b["source_gtfs_rows"], h["events"], h["edges"], h["states"]


def _place(b):
    h = b["identity_history"]
    return b["snapshot"], b["gtfs_status_rows"], h["events"], h["edges"], h["states"]


ADAPTERS = {
    "dc_ward": ("dc-ward-evidence-package-v1", _ward),
    "dc_anc": ("dc_anc_private_evidence_v1", _anc),
    "county": ("county_private_evidence_v1", _county),
    "state": ("state_private_evidence_v1", _state),
    "census_place": ("Census_place_private_evidence_v1", _place),
}


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _id(value):
    _require(type(value) is int and value > 0, "invalid_physical_stop_id")
    return value


def _hash(value, expected):
    _require(isinstance(expected, str) and digest(value) == expected.lower(), "hash_mismatch")


def _sealed(body):
    return {**body, "report_sha256": digest(body)}


def build_cross_dimension_report(packages):
    """Accept a dimension->JSON-envelope mapping; return a sealed report.

    Invalid inputs quarantine the entire report. No supplied paths are opened.
    Input byte hashes cannot be inferred from parsed JSON; payload hashes are used.
    """
    base = {"format": FORMAT, "purpose": "evidence_adjudication_only",
            "issuance_ready": False, "certification_action": "none"}
    try:
        return _build(deepcopy(packages), base)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        code = str(exc) if isinstance(exc, ValueError) else "malformed_package"
        return _sealed({**base, "status": "quarantined", "errors": [code],
                        "validation_details": {"stage": "input_validation", "code": code},
                        "stop_records": [], "active_stop_denominator": None})


def _build(packages, base):
    _require(isinstance(packages, dict) and set(packages) == set(DIMENSIONS), "five_packages_required")
    data, hashes, active_sets, snapshots = {}, {}, [], []
    reference_events = reference_edges = None
    states_by_id = {}
    for dim in DIMENSIONS:
        envelope = packages[dim]
        b = envelope["evidence_package"]
        _hash(b, envelope["evidence_package_sha256"])
        fmt, adapter = ADAPTERS[dim]
        _require(b["format"] == fmt, "unsupported_package_format")
        snapshot, statuses, events, edges, states = adapter(b)
        _require(isinstance(snapshot["sha256"], str) and len(snapshot["sha256"]) == 64
                 and all(c in "0123456789abcdef" for c in snapshot["sha256"]), "invalid_snapshot_hash")
        snapshots.append(snapshot["sha256"])
        status_map = {}
        for row in statuses:
            sid = _id(row["physical_stop_id"])
            _require(sid not in status_map and type(row["current_gtfs"]) is int, "invalid_active_status")
            status_map[sid] = row["current_gtfs"]
        active = {sid for sid, status in status_map.items() if status == 1}
        active_sets.append(active)
        event_value = sorted(events, key=canonical)
        edge_value = sorted(edges, key=canonical)
        if reference_events is None:
            reference_events, reference_edges = event_value, edge_value
        _require(event_value == reference_events and edge_value == reference_edges, "identity_history_disagreement")
        for state in states:
            sid = _id(state["physical_stop_id"])
            _require(sid not in states_by_id or states_by_id[sid] == state, "identity_state_disagreement")
            states_by_id[sid] = state
        seen = set()
        for scope in b["scope_records"]:
            meta = scope["metadata"]
            _hash(meta, scope.get("metadata_sha256", scope.get("scope_metadata_sha256")))
            _hash(scope["membership"], scope["membership_sha256"])
            if "coordinate_discovery_members" in scope:
                _hash(scope["coordinate_discovery_members"], scope["coordinate_discovery_members_sha256"])
            key = meta["scope_key"]
            _require(meta["certification_status"] == "pending_independent_review"
                     and meta["certification_reference"] is None, "unsupported_certification_status")
            _require(isinstance(key, str) and key and key not in seen, "duplicate_or_invalid_scope")
            seen.add(key)
            ids = []
            for member in scope["membership"]:
                sid = _id(member["physical_stop_id"])
                _require(type(member["current_gtfs"]) is int and member["current_gtfs"] == 1
                         and sid in active, "invalid_scope_member")
                ids.append(sid)
            _require(len(ids) == len(set(ids)), "duplicate_scope_member")
        hashes[dim] = digest(b)
        data[dim] = b
    _require(all(a == active_sets[0] for a in active_sets), "active_denominator_disagreement")
    _require(len(set(snapshots)) == 1, "snapshot_disagreement")
    _require(data["census_place"]["state_evidence_reference"]["package_sha256"] == hashes["state"],
             "state_reference_mismatch")
    return _reconcile(data, hashes, active_sets[0], snapshots[0], base)


def _clean(value):
    """Do not export capture/edit timestamps or local machine paths."""
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()
                if not any(t in k.lower() for t in ("timestamp", "created", "updated", "edited", "path"))
                and not k.endswith(("_at", "_utc"))}
    return value


def _state(meta):
    identity = meta.get("source_identity", meta.get("canonical_identity", {}))
    return meta.get("state") or {"11": "DC", "24": "MD", "51": "VA"}.get(
        identity.get("STATEFP", identity.get("state_fips")))


def _normalize(label):
    return " ".join(str(label).casefold().split())


def _reconcile(data, hashes, active, snapshot, base):
    # This entire phase validates comparable evidence before allocating records.
    asserted_sources, source_claims, warnings = {}, [], []
    native = {}
    for dim, b in data.items():
        snap, statuses, events, edges, states = ADAPTERS[dim][1](b)
        manifest = snap.get("manifest", snap.get("snapshot_manifest"))
        if manifest is not None:
            _require(manifest["backup_sha256"].lower() == snapshot, "embedded_snapshot_mismatch")
        # Snapshot manifest hashes describe file bytes, not canonical JSON; retain
        # as unverified references instead of pretending to recompute them.
        def claim(name, value):
            if not name or not value:
                return
            _require(isinstance(value, str) and len(value) == 64 and
                     all(c in "0123456789abcdefABCDEF" for c in value), "invalid_source_hash")
            name = name.replace("\\", "/").split("/")[-1].removesuffix(".geojson")
            _require(name not in asserted_sources or asserted_sources[name] == value.lower(),
                     "source_artifact_hash_disagreement")
            asserted_sources[name] = value.lower()
            source_claims.append({"dimension": dim, "artifact": name, "sha256": value.lower()})
        for name, source in b.get("sources", {}).items():
            claim(name, source.get("sha256"))
        boundary = b.get("boundary", b.get("retained_boundary", {}))
        claim(boundary.get("path", boundary.get("artifact")), boundary.get("sha256"))
        for scope in b["scope_records"]:
            m = scope["metadata"]
            claim(m.get("boundary_artifact", m.get("source_artifact")),
                  m.get("boundary_sha256", m.get("source_sha256")))
            for name, value in m.get("source_artifact_hashes", {}).items():
                claim(name, value)
        rows = b.get("active_stop_evidence", b.get("active_stop_original_evidence", []))
        rowmap = {}
        for r in rows:
            sid = _id(r["physical_stop_id"])
            _require(sid not in rowmap, "duplicate_discovery_row")
            rowmap[sid] = r
        labels = b.get("original_jurisdiction_rows", b.get("original_stop_jurisdiction_rows", []))
        labelmap = {}
        for r in labels:
            sid = _id(r["stop_id"])
            _require(sid not in labelmap, "duplicate_stored_label_row")
            labelmap[sid] = r
        statemap = {}
        for r in states:
            sid = _id(r["physical_stop_id"])
            _require(sid not in statemap, "duplicate_identity_state")
            _require(r.get("identity_status") in ("current", "retired", "manual_exception"),
                     "invalid_identity_status")
            statemap[sid] = r
        eventmap = {e["id"]: e for e in events}
        _require(len(eventmap) == len(events), "duplicate_identity_event")
        _require(all(type(eid) is int and eid > 0 for eid in eventmap), "invalid_event_id")
        for e in edges:
            _require(type(e["event_id"]) is int and e["event_id"] in eventmap, "unknown_edge_event")
            for k in ("predecessor_physical_stop_id", "successor_physical_stop_id"):
                _id(e[k])  # Retired predecessors need not be active.
                if dim != "dc_ward" and e[k] not in statemap:
                    warnings.append((dim, e[k], "edge_identity_evidence_missing"))
        for r in states:
            if r.get("retirement_event_id") is not None:
                _require(r["retirement_event_id"] in eventmap, "unknown_retirement_event")
        edge_events = {e["event_id"] for e in edges}
        if set(eventmap) - edge_events:
            warnings.append((dim, None, "events_without_attributable_edges"))
        expected = active if dim != "dc_ward" else {
            m["physical_stop_id"] for s in b["scope_records"] for m in s["membership"]}
        for sid in sorted(expected - set(statemap)):
            warnings.append((dim, sid, "identity_state_missing"))
        for sid in sorted(active - set(rowmap)):
            warnings.append((dim, sid, "discovery_evidence_missing"))
        native[dim] = {"rows": rowmap, "labels": labelmap, "states": statemap,
                       "edges": edges, "events": events}
    for sid, r in native["census_place"]["rows"].items():
        embedded = r.get("state_cross_source_evidence")
        if embedded is None:
            warnings.append(("census_place", sid, "embedded_state_evidence_missing"))
        else:
            _require(embedded == native["state"]["rows"].get(sid), "embedded_state_content_mismatch")

    indexes, categories, records = {}, {}, {}
    for sid in sorted(active):
        records[sid] = {"physical_stop_id": sid, "active_membership_status": 1,
                       "dimensions": {}, "findings": [], "issuance_ready": False}
    def flag(sid, dim, code, kind, details=None):
        key = dim + ":" + code
        indexes.setdefault(key, set()).add(sid)
        categories.setdefault(code, set()).add(sid)
        finding = {"dimension": dim, "code": code, "kind": kind, "details": details}
        if finding not in records[sid]["findings"]:
            records[sid]["findings"].append(finding)
    memberships = {}
    for dim in DIMENSIONS:
        memberships[dim] = {sid: [] for sid in active}
        for s in sorted(data[dim]["scope_records"], key=lambda x: x["metadata"]["scope_key"]):
            for member in s["membership"]:
                memberships[dim][member["physical_stop_id"]].append({
                    "metadata": _clean(s["metadata"]), "scope_key": s["metadata"]["scope_key"],
                    "membership_sha256": s["membership_sha256"], "package_sha256": hashes[dim]})
    catalogs = {}
    for dim in ("county", "census_place"):
        b = data[dim]
        catalog = b.get("boundary", {}).get("all_source_feature_properties", []) if dim == "county" else [
            p for source in b.get("sources", {}).values() for p in source.get("all_feature_properties", [])]
        catalogs[dim] = catalog
    for sid, record in records.items():
        for dim in DIMENSIONS:
            n = native[dim]
            supplied = memberships[dim][sid]
            raw = n["rows"].get(sid)
            labels = n["labels"].get(sid)
            state = n["states"].get(sid)
            event_ids = sorted({e["event_id"] for e in n["edges"] if sid in
                                (e["predecessor_physical_stop_id"], e["successor_physical_stop_id"])})
            d = {"supplied_memberships": supplied, "separately_reported_discoveries": _clean(raw),
                 "stored_labels": labels, "absence_status": "present" if supplied else "no_supplied_membership",
                 "comparable_assertions_used": [], "assessment": None, "unresolved_evidence": [],
                 "classification_notices": [], "package_sha256": hashes[dim],
                 "identity_history": {"state": _clean(state), "status": state["identity_status"] if state else "unknown",
                     "manual_exception": state["identity_status"] == "manual_exception" if state else None,
                     "event_ids": event_ids}}
            record["dimensions"][dim] = d
            if not supplied:
                flag(sid, dim, "no_supplied_membership", "absence")
            if len(supplied) > 1:
                flag(sid, dim, "multiple_supplied_memberships", "unresolved")
            if labels is None:
                flag(sid, dim, "stored_label_evidence_missing", "unresolved")
            if supplied:
                for code in ("CRS_unresolved", "historical_effective_date_unresolved"):
                    flag(sid, dim, code, "unresolved")
                if event_ids:
                    flag(sid, dim, "identity_edge_involvement", "identity")
                if state is None:
                    flag(sid, dim, "identity_evidence_incomplete", "unresolved")
                elif state["identity_status"] != "current":
                    flag(sid, dim, "noncurrent_identity_state", "identity")
                    if state["identity_status"] == "manual_exception":
                        flag(sid, dim, "manual_exception", "identity")
            for m in supplied:
                classification = m["metadata"].get("classification", "")
                identity = m["metadata"].get("source_identity", {})
                asserted_state = _state(m["metadata"])
                source_state = _state({"source_identity": identity})
                if source_state and asserted_state != source_state:
                    flag(sid, dim, "source_state_assertion_disagreement", "contradiction",
                         {"metadata_state": asserted_state, "source_state": source_state})
                code = ("independent_city_county_equivalent" if "independent_city" in classification else
                        "CDP_not_incorporated_place" if classification == "CDP" else
                        "incorporated_place_classification" if "incorporated" in classification else None)
                if code:
                    flag(sid, dim, code, "classification", m["scope_key"])
            if dim in ("county", "census_place"):
                field = "county" if dim == "county" else "municipality"
                label = (labels or {}).get(field)
                identities = [m["metadata"].get("source_identity", {}) for m in supplied]
                discovery_key = "coordinate_matches" if dim == "county" else "coordinate_place_geoids"
                discoveries = raw.get(discovery_key) if raw else None
                d["comparable_assertions_used"].append({"stored_label": label, "supplied_identities": identities,
                                                         "coordinate_geoids": discoveries})
                if discoveries is None:
                    flag(sid, dim, "coordinate_evidence_missing", "unresolved")
                else:
                    supplied_ids = sorted(i.get("GEOID") for i in identities if i.get("GEOID"))
                    if supplied_ids != sorted(discoveries):
                        flag(sid, dim, "supplied_vs_coordinate_disagreement", "contradiction")
                    byid = {p["GEOID"]: p for p in catalogs[dim]}
                    names = [byid[g] for g in discoveries if g in byid]
                    if len(names) != len(discoveries):
                        flag(sid, dim, "discovery_identity_missing", "unresolved")
                    if label and names and not any(_normalize(label) in
                            (_normalize(i.get("NAME", "")), _normalize(i.get("NAMELSAD", ""))) for i in names):
                        flag(sid, dim, "source_label_disagreement", "contradiction")
                    if label and not discoveries:
                        flag(sid, dim, "stored_label_without_coordinate_membership", "contradiction")
                    if label is None:
                        flag(sid, dim, "null_stored_label", "absence")
                        if discoveries:
                            flag(sid, dim, "null_label_with_coordinate_membership", "contradiction")
                if not catalogs[dim]:
                    flag(sid, dim, "crosswalk_catalog_missing", "unresolved")
                elif label:
                    candidates = [p for p in catalogs[dim] if _normalize(label) in
                                  (_normalize(p.get("NAME", "")), _normalize(p.get("NAMELSAD", "")))]
                    context = [p for p in candidates if _state({"source_identity": p}) == (labels or {}).get("state")]
                    d["comparable_assertions_used"].append({"global_candidates": candidates, "state_context_candidates": context})
                    if len(candidates) > 1:
                        flag(sid, dim, "ambiguous_global_crosswalk", "unresolved")
                    if len(context) > 1:
                        flag(sid, dim, "ambiguous_state_context_crosswalk", "unresolved")
                state_assertions = {_state(m["metadata"]) for m in memberships["state"][sid]}
                boundary_states = {_state(m["metadata"]) for m in supplied}
                d["comparable_assertions_used"].append({"state_membership": sorted(s for s in state_assertions if s),
                                                         "boundary_states": sorted(s for s in boundary_states if s)})
                if None in boundary_states or not state_assertions:
                    flag(sid, dim, "state_assertion_missing", "unresolved")
                if boundary_states - {None} and state_assertions - {None} and boundary_states != state_assertions:
                    flag(sid, dim, "state_boundary_conflict", "contradiction")
            if dim == "state":
                derived = raw.get("pipeline_result", {}).get("state") if raw else None
                supplied_states = {_state(m["metadata"]) for m in supplied}
                d["comparable_assertions_used"].append({"pipeline_state": derived, "supplied_states": sorted(s for s in supplied_states if s)})
                if derived is None:
                    flag(sid, dim, "pipeline_evidence_missing", "unresolved")
                elif supplied_states != {derived}:
                    flag(sid, dim, "coordinate_vs_stored_disagreement", "contradiction")
            if dim in ("dc_ward", "dc_anc"):
                # The Ward format supplies its discovery population per scope.
                if dim == "dc_ward":
                    discovered = [s["metadata"]["scope_key"] for s in data[dim]["scope_records"]
                                  if sid in s.get("coordinate_discovery_members", [])]
                    expected = [m["scope_key"] for m in supplied]
                    if sorted(discovered) != sorted(expected):
                        flag(sid, dim, "coordinate_vs_stored_disagreement", "contradiction")
                    d["comparable_assertions_used"].append({"coordinate_scope_keys": discovered, "supplied_scope_keys": expected})
                    ward_values = [m["metadata"].get("canonical_geography_identity", {}).get("WARD") for m in supplied]
                    label = (labels or {}).get("dc_ward")
                    if supplied and (label is None or any(v is None for v in ward_values)):
                        flag(sid, dim, "ward_label_identity_evidence_missing", "unresolved")
                    elif supplied:
                        candidate = str(label)
                        if candidate.endswith(".0"):
                            candidate = candidate[:-2]
                        if candidate not in [str(v) for v in ward_values]:
                            flag(sid, dim, "source_label_disagreement", "contradiction")
                        elif str(label) != candidate:
                            flag(sid, dim, "ward_numeric_label_equivalence", "classification",
                                 {"original": label, "candidate": candidate, "status": "unreviewed_crosswalk"})
                else:
                    found = raw.get("polygon_matches") if raw else None
                    expected = [m["metadata"].get("source_identity", {}).get("ANC_ID") for m in supplied]
                    if found is None:
                        flag(sid, dim, "coordinate_evidence_missing", "unresolved")
                    elif sorted(found) != sorted(x for x in expected if x):
                        flag(sid, dim, "coordinate_vs_stored_disagreement", "contradiction")
                    if labels and found and labels.get("dc_anc") not in found:
                        flag(sid, dim, "source_label_disagreement", "contradiction")
                supplied_states = {_state(m["metadata"]) for m in memberships["state"][sid]}
                if supplied and supplied_states != {"DC"}:
                    flag(sid, dim, "state_boundary_conflict", "contradiction")
        county = memberships["county"][sid]
        place = memberships["census_place"][sid]
        for cm in county:
            for pm in place:
                ci, pi = cm["metadata"].get("source_identity", {}), pm["metadata"].get("source_identity", {})
                if ci.get("STATEFP") and pi.get("STATEFP") and ci["STATEFP"] != pi["STATEFP"]:
                    flag(sid, "census_place", "county_place_state_disagreement", "contradiction",
                         {"county_STATEFP": ci["STATEFP"], "place_STATEFP": pi["STATEFP"]})
                if ci.get("CLASSFP") == "C7" and pi.get("CLASSFP") == "C7":
                    record["dimensions"]["census_place"]["comparable_assertions_used"].append({"county_equivalent": ci, "independent_city_place": pi})
                    if (ci.get("STATEFP"), ci.get("NAME")) != (pi.get("STATEFP"), pi.get("NAME")):
                        flag(sid, "census_place", "county_place_identity_disagreement", "contradiction")
    for dim, sid, code in warnings:
        if sid in active:
            flag(sid, dim, "identity_evidence_incomplete" if "identity" in code else code, "unresolved", code)
    for r in records.values():
        r["findings"] = sorted(r["findings"], key=canonical)
        for dim, d in r["dimensions"].items():
            findings = [f for f in r["findings"] if f["dimension"] == dim]
            d["classification_notices"] = [f for f in findings if f["kind"] == "classification"]
            d["unresolved_evidence"] = [f for f in findings if f["kind"] == "unresolved"]
            d["assessment"] = "disagreement" if any(f["kind"] == "contradiction" for f in findings) else "unresolved" if d["unresolved_evidence"] else "no_comparable_disagreement"
    combinations_index = {}
    for sid, r in records.items():
        signature = canonical(sorted({f["dimension"] + ":" + f["code"] for f in r["findings"]}))
        combinations_index.setdefault(signature, []).append(sid)
    return _sealed({**base, "status": "pending_adjudication", "input_package_hashes": hashes,
        "active_stop_denominator": len(active), "snapshot_sha256": snapshot, "stop_records": list(records.values()),
        "provenance": {"canonical_payloads_metadata_memberships": "verified_from_supplied_JSON",
                       "source_artifact_hashes": asserted_sources, "source_artifact_bytes": "unavailable_not_verified",
                       "snapshot_manifest_file_hashes": "asserted_file_bytes_unavailable"},
        "dimension_counts": {d: {"represented": sum(bool(x) for x in memberships[d].values()),
                                  "missing": sum(not x for x in memberships[d].values())} for d in DIMENSIONS},
        "category_counts": {k: len(v) for k, v in sorted(categories.items())},
        "affected_stop_indexes": {k: {"count": len(v), "physical_stop_ids": sorted(v)} for k, v in sorted(indexes.items())},
        "intersections": [{"left": a, "right": b, "count": len(indexes[a] & indexes[b]),
                           "physical_stop_ids": sorted(indexes[a] & indexes[b])} for a, b in combinations(sorted(indexes), 2)],
        "exact_finding_combinations": combinations_index,
        "identity_history_findings": [{"dimension": d, "physical_stop_id": sid, "code": code}
                                      for d, sid, code in sorted(warnings, key=canonical)],
        "unresolved_blockers": ["independent_certification", "historical_membership_attribution", "effective_dates",
                                "CRS_compatibility", "source_provenance", "identity_history_review", "crosswalk_review"]
            + sorted({code for _, _, code in warnings})})

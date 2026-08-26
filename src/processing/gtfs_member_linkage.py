"""Transparent GTFS-to-member identity precedence for stop diagnostics."""

EXACT_METHODS = frozenset({"wmata_stop_code", "exact_stop_code", "explicit_crosswalk"})


def classify_member_links(external_stop_id, mappings):
    """Classify mappings without deleting weaker provenance.

    Exact source identity outranks coordinate matching. If exact identity is absent,
    coordinate matches remain usable but explicitly unresolved. Multiple different
    exact GTFS identities fail closed.
    """
    external = str(external_stop_id) if external_stop_id is not None else None
    exact = [m for m in mappings if m.get("match_method") in EXACT_METHODS and
             (m.get("stop_code") is None or str(m.get("stop_code")) == external)]
    exact_ids = {str(m.get("gtfs_stop_id")) for m in exact}
    conflicting_exact = len(exact_ids) > 1
    result = []
    for mapping in mappings:
        item = dict(mapping)
        is_exact = mapping in exact
        if is_exact:
            kind = "unresolved" if conflicting_exact else "exact_identity"
        elif exact:
            kind = "conflicting_fallback"
        elif mapping.get("match_method") == "coordinate":
            kind = "coordinate_fallback"
        else:
            kind = "unresolved"
        item["linkage_classification"] = kind
        item["identity_eligible"] = kind in {"exact_identity", "coordinate_fallback"}
        result.append(item)
    return result


def identity_eligible_mappings(external_stop_id, mappings):
    return [m for m in classify_member_links(external_stop_id, mappings)
            if m["identity_eligible"]]

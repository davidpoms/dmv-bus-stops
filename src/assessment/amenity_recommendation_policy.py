"""Shared, fail-closed amenity recommendation provenance policy."""

ELIGIBLE_LOCAL_NEGATIVE_SOURCES = {
    "ALEXANDRIA",
    "MONTGOMERY_COUNTY_WMATA",
    "PRINCE_GEORGES_COUNTY_THEBUS",
}

LOCAL_SOURCE_JURISDICTIONS = {
    "ALEXANDRIA": ("VA", "Alexandria"),
    "MONTGOMERY_COUNTY_WMATA": ("MD", "Montgomery"),
    "PRINCE_GEORGES_COUNTY_THEBUS": ("MD", "Prince George's"),
}

LOCAL_SOURCE_PUBLIC_LABELS = {
    "ALEXANDRIA": "City of Alexandria inventory",
    "MONTGOMERY_COUNTY_WMATA": "Montgomery County inventory",
    "PRINCE_GEORGES_COUNTY_THEBUS": "Prince George's County TheBus inventory",
}


def source_applies_to_jurisdiction(source, state, county):
    """Return true only for a known source inside its authority boundary."""
    return LOCAL_SOURCE_JURISDICTIONS.get(source) == (state, county)


def classify_negative_evidence(status, negative_evidence=None):
    """Classify installation provenance without changing canonical truth."""
    negative_evidence = negative_evidence or {}
    high_sources = sorted(
        set(negative_evidence.get("high_local_sources", ()))
        & ELIGIBLE_LOCAL_NEGATIVE_SOURCES
    )
    medium_sources = sorted(
        set(negative_evidence.get("medium_local_sources", ()))
        & ELIGIBLE_LOCAL_NEGATIVE_SOURCES
    )
    osm_negative = bool(negative_evidence.get("osm_negative"))
    community_negative = bool(negative_evidence.get("community_negative"))
    classes = [
        name for name, present in (
            ("local_jurisdiction", bool(high_sources or medium_sources)),
            ("identity_matched_osm", osm_negative),
            ("community_observation", community_negative),
        ) if present
    ]
    corroborated = len(classes) >= 2
    eligible = status == "confirmed_no" or (
        status == "likely_no" and (bool(high_sources) or corroborated)
    )
    if status == "confirmed_no":
        strength = "confirmed_absence"
        confidence = "high"
    elif corroborated:
        strength = "corroborated_likely_absence"
        confidence = "medium"
    elif high_sources:
        strength = "supported_local_likely_absence"
        confidence = "medium"
    else:
        strength = "insufficient_for_installation"
        confidence = None
    return {
        "eligible": eligible,
        "evidence_strength": strength,
        "recommendation_confidence": confidence,
        "negative_evidence_classes": classes,
        "eligible_local_negative_sources": sorted(set(high_sources + medium_sources)),
        "local_match_quality": (
            "high" if high_sources else "medium" if medium_sources else None
        ),
        "osm_negative": osm_negative,
        "community_negative": community_negative,
    }

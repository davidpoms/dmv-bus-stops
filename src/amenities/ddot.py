"""Pure helpers for safe DDOT ArcGIS shelter imports."""

import hashlib
import json
import math


def _clean(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_source_record_id(attrs, latitude, longitude):
    barcode = _clean(attrs.get("Barcode"))
    if barcode:
        return f"barcode:{barcode.upper()}"
    panel = _clean(attrs.get("Panel_No"))
    if panel:
        return f"panel:{panel}"
    site = _clean(attrs.get("Site_Code"))
    if site and latitude is not None and longitude is not None:
        return f"site-location:{site}:{latitude:.6f}:{longitude:.6f}"
    canonical = {
        "attributes": {key: attrs[key] for key in sorted(attrs)},
        "latitude": None if latitude is None else round(latitude, 6),
        "longitude": None if longitude is None else round(longitude, 6),
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
        .encode("utf-8")
    ).hexdigest()
    return f"feature-sha256:{digest}"


def feature_coordinates(feature):
    geometry = feature.get("geometry") or {}
    attrs = feature.get("attributes") or {}
    latitude = geometry.get("y", attrs.get("Latitude"))
    longitude = geometry.get("x", attrs.get("Longitude"))
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return None
    return latitude, longitude


def percentile(sorted_values, percent):
    if not sorted_values:
        return None
    position = (len(sorted_values) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction

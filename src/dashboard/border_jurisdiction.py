"""Display-only border convention. No geography, identity, or recognition mutation."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from types import MappingProxyType

SOURCE_REPORT_SHA256 = "d196caa9c065bacf4a42bac3f526b6c7466744d06ce8cd71c98c416e19cc0682"
ARTIFACT_SHA256 = "42d1aa2d9357d9e545cfb8d750d675b16891556f78a18c3f20f1b6f67a4dcd76"
IDS_SHA256 = "f04d0963ef9d348e10797ffdeeae438f45c9306144bf2d86adc2dfb1496eb98c"
UNRESOLVED_IDS = frozenset((1064, 1253, 1409, 1444, 7003, 7731))


class BorderPolicyUnavailable(ValueError):
    """The pinned operational policy is unavailable or invalid."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def validate_policy(artifact):
    """Validate an already parsed artifact; return immutable lookup values."""
    try:
        if set(artifact) != {"format", "source_report_sha256", "stops"}:
            raise ValueError("invalid_structure")
        if artifact["format"] != "border-operational-jurisdiction-v1":
            raise ValueError("invalid_format")
        if artifact["source_report_sha256"] != SOURCE_REPORT_SHA256:
            raise ValueError("wrong_source_report_hash")
        rows = artifact["stops"]
        if not isinstance(rows, list) or len(rows) != 147:
            raise ValueError("wrong_population")
        ids = [r["physical_stop_id"] for r in rows]
        if any(type(i) is not int for i in ids) or len(set(ids)) != 147:
            raise ValueError("duplicate_or_invalid_id")
        if ids != sorted(ids) or hashlib.sha256(_canonical(ids)).hexdigest() != IDS_SHA256:
            raise ValueError("wrong_id_population_or_order")
        fields = {"physical_stop_id", "value", "jurisdiction_basis", "border_notice",
                  "border_review_required", "border_notice_reasons"}
        for row in rows:
            if set(row) != fields or row["value"] not in ("DC", "MD", None):
                raise ValueError("invalid_fields_or_value")
            unresolved = row["physical_stop_id"] in UNRESOLVED_IDS
            basis = "unresolved_border_review" if unresolved else "border_centerline_convention"
            if (row["value"] is None) != unresolved or row["jurisdiction_basis"] != basis:
                raise ValueError("invalid_basis_or_unresolved")
            reasons = row["border_notice_reasons"]
            if (row["border_notice"] is not True
                    or type(row["border_review_required"]) is not bool
                    or not isinstance(reasons, list)
                    or any(not isinstance(s, str) or not s for s in reasons)
                    or reasons != sorted(set(reasons))
                    or row["border_review_required"] != bool(reasons)):
                raise ValueError("invalid_warning")
            if unresolved and reasons != ["centerline_unresolved"]:
                raise ValueError("invalid_unresolved_warning")
        if Counter(r["value"] for r in rows) != {"DC": 82, "MD": 59, None: 6}:
            raise ValueError("wrong_counts")
        if hashlib.sha256(_canonical(artifact)).hexdigest() != ARTIFACT_SHA256:
            raise ValueError("wrong_artifact_hash")
        return MappingProxyType({r["physical_stop_id"]: MappingProxyType({
            **{k: v for k, v in r.items() if k not in ("physical_stop_id", "border_notice_reasons")},
            "border_notice_reasons": tuple(r["border_notice_reasons"]),
        }) for r in rows})
    except (ValueError, TypeError, KeyError) as exc:
        raise BorderPolicyUnavailable(str(exc)) from exc


def _load_policy():
    try:
        return validate_policy(json.loads(Path(__file__).with_name(
            "border_jurisdiction_policy.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return None


# One startup read. Never read files, databases, or network during lookup.
_POLICY = _load_policy()


def operational_jurisdiction(physical_stop_id):
    if _POLICY is None:
        raise BorderPolicyUnavailable("border_policy_unavailable")
    if type(physical_stop_id) is not int:
        return None
    value = _POLICY.get(physical_stop_id)
    if value is None:
        return None
    return {**value, "border_notice_reasons": list(value["border_notice_reasons"])}

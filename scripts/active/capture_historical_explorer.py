"""Explicit production capture for the reviewed 55/14 cohort; never issuance."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.active import issue_historical_explorer as issuance
from scripts.active.rehearse_recognition_capture import (
    check_state, file_hash, offline_file, read_manifest, require,
)
from src.review.recognition import RecognitionGate
from src.review.recognition.backfill import capture_batch, source_plan
from src.review.recognition.rules import RULE_KEY, canonical, digest
from src.review.recognition.schema import connection


def binding_for_capture(target):
    """Reuse the exact production identity validator without authorizing issuance."""
    supplied = json.loads(issuance.BINDING_PATH.read_text(encoding="utf-8"))
    require(isinstance(supplied, dict), "invalid_target_binding")
    binding = issuance.target_binding(target, supplied.get("issuance_manifest_sha256"),
                                      supplied.get("snapshot_sha256"))
    require(binding == supplied, "target_binding_changed")
    return binding


def check_source(conn, manifest):
    current = source_plan(conn, RULE_KEY, after_assignment=141, through_assignment=210,
                          limit=manifest["cohort"]["limit"],
                          sqlite_utc_provenance=manifest["sqlite_utc_provenance"])
    require(all(current[k] == manifest[k] for k in current), "reviewed_manifest_mismatch")


def capture_historical(production_db, manifest_path, *, capture_production=False):
    target = offline_file(production_db)
    manifest_path = Path(manifest_path)
    binding = binding_for_capture(target)
    issuance.announce("capture-target-verification", binding)
    manifest = read_manifest(manifest_path, binding["capture_manifest_sha256"], 55, 14)
    require(manifest["cohort"]["after_assignment"] == 141
            and manifest["cohort"]["through_assignment"] == 210, "historical_cohort_required")
    with connection(target) as conn:
        conn.execute("BEGIN")
        issuance.full_checks(conn)
        schema = issuance.schema_identity(conn)
        check_source(conn, manifest)
        cohort = issuance.cohort_fingerprint(conn, manifest)
        state = check_state(conn, manifest, allow_empty=True)

    def recheck_artifacts():
        require(binding_for_capture(target) == binding, "target_binding_changed")
        require(file_hash(manifest_path) == binding["capture_manifest_sha256"].lower(),
                "manifest_hash_mismatch")

    def transaction_guard(conn, phase):
        recheck_artifacts()
        require(issuance.schema_identity(conn) == schema, "schema_changed")
        check_source(conn, manifest)
        require(issuance.cohort_fingerprint(conn, manifest) == cohort, "historical_cohort_changed")
        if phase == "before_capture":
            require(check_state(conn, manifest, allow_empty=True) == state,
                    "concurrent_recognition_state_change")
        elif phase == "before_commit":
            check_state(conn, manifest, allow_empty=False)
        else:
            raise ValueError("unexpected_capture_guard_phase")

    if capture_production:
        issuance.announce("capture-authorization-boundary", binding,
                          capture_manifest_sha256=binding["capture_manifest_sha256"],
                          qualified=55, excluded=14, issuance_enabled=False)
        recheck_artifacts()
        capture_batch(target, manifest, gate=RecognitionGate(capture=True, issuance=False),
                      transaction_guard=transaction_guard)
    with connection(target) as conn:
        conn.execute("BEGIN")
        issuance.full_checks(conn)
        check_source(conn, manifest)
        state = check_state(conn, manifest, allow_empty=not capture_production)
    recheck_artifacts()
    captured = state == "captured"
    return {"mode": "capture-production" if capture_production else "verify-only",
            "target": str(target), "environment": binding["environment"], "hostname": binding["hostname"],
            "binding_sha256": digest(binding), "capture_manifest_sha256": binding["capture_manifest_sha256"],
            "snapshot_sha256_reference": binding["snapshot_sha256"], "rule_key": RULE_KEY,
            "qualified": 55, "excluded": 14, "state": state,
            "completions": 55 if captured else 0, "pending_jobs": 55 if captured else 0,
            "attempts": 0, "leases": 0, "awards": 0, "witnesses": 0,
            "runs": 1 if captured else 0, "run_id": digest(manifest) if captured else None,
            "integrity_check": "ok", "issuance_enabled": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-db", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True, help="Original reviewed capture manifest file")
    parser.add_argument("--capture-production", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = capture_historical(args.production_db, args.manifest,
                                    capture_production=args.capture_production)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, canonical({"error": str(error), "issuance_enabled": False,
                                "action": "Inspect verification-only state before retrying"}) + "\n")
    print(canonical(result))


if __name__ == "__main__":
    main()

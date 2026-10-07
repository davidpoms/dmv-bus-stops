"""Disposable-only new-family migration/sealing rehearsal. No production mode."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.active.rehearse_recognition_capture import file_hash, offline_file
from src.review.recognition import RecognitionGate
from src.review.recognition.permanent import finalize, prepare, require
from src.review.recognition.permanent_schema import migrate
from src.review.recognition.rules import canonical, digest
from src.review.recognition.schema import TABLES as EXPLORER_TABLES, connection


def _target(path):
    supplied = Path(path).absolute()
    root = ROOT / ".tmp" / "private-recognition-rehearsals"
    require(supplied.parent == root and supplied.name.startswith("disposable-") and
            supplied.suffix == ".db", "reserved_disposable_target_required")
    for item in (supplied, *supplied.parents):
        require(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)(), "target_alias_rejected")
    require(supplied.resolve() == supplied, "target_alias_rejected")
    return supplied


def _explorer_rows(path):
    with connection(path) as conn:
        conn.execute("BEGIN")
        return {table: sorted([dict(r) for r in conn.execute(f"SELECT * FROM {table}")], key=canonical)
                for table in EXPLORER_TABLES}


def run(*, source, source_sha256, manifest_path, manifest_sha256, target,
        apply_disposable=False, retry_existing=False, authorization_reference=None):
    source = offline_file(source)
    target = _target(target)
    manifest_path = Path(manifest_path).resolve(strict=True)
    require(file_hash(source) == source_sha256.lower(), "source_hash_mismatch")
    require(file_hash(manifest_path) == manifest_sha256.lower(), "manifest_file_hash_mismatch")
    require(target != source and (not target.exists() or not os.path.samefile(source, target)), "source_target_alias")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fresh = prepare(source, family=manifest["family"], inputs=manifest["inputs"],
                    evaluation_at_utc=manifest["evaluation_at_utc"],
                    authorization_reference=manifest["authorization_reference"])
    require(fresh == manifest, "reviewed_manifest_mismatch")
    migrate(source)  # read-only source -> in-memory migration rehearsal
    with connection(source) as conn:
        require(conn.execute("PRAGMA integrity_check").fetchall()[0][0] == "ok", "source_integrity_failed")
        require(conn.execute("PRAGMA foreign_key_check").fetchone() is None, "source_foreign_key_failed")
    result = {"mode": "verification_only", "production_authorized": False,
              "source_sha256": source_sha256.lower(), "manifest_file_sha256": manifest_sha256.lower(),
              "canonical_manifest_sha256": digest(manifest), "family": manifest["family"],
              "candidates": len(manifest["candidates"]), "target": str(target)}
    if not apply_disposable:
        require(not retry_existing, "retry_requires_disposable_authorization")
        require(file_hash(source) == source_sha256.lower(), "source_changed")
        return result
    require(authorization_reference == manifest["authorization_reference"] and bool(authorization_reference),
            "explicit_authorization_required")
    before = _explorer_rows(source)
    receipt_path = target.with_suffix(".receipt.json")
    identity = {"source_sha256": source_sha256.lower(), "manifest_file_sha256": manifest_sha256.lower(),
                "canonical_manifest_sha256": digest(manifest), "target": str(target),
                "purpose": "disposable_private_recognition_rehearsal"}
    if retry_existing:
        offline_file(target)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        stat = target.stat()
        require(receipt == {**identity, "device": stat.st_dev, "inode": stat.st_ino} and stat.st_nlink == 1,
                "disposable_receipt_mismatch")
    else:
        require(not target.exists() and not receipt_path.exists(), "new_disposable_target_required")
        target.parent.mkdir(parents=True, exist_ok=True)
        _target(target)  # recheck ancestors after directory creation
        with source.open("rb") as inp, target.open("xb") as out:
            shutil.copyfileobj(inp, out)
        require(file_hash(target) == source_sha256.lower() == file_hash(source), "copy_hash_mismatch")
        stat = target.stat()
        with receipt_path.open("x", encoding="utf-8") as stream:
            stream.write(canonical({**identity, "device": stat.st_dev, "inode": stat.st_ino}))
    require(file_hash(manifest_path) == manifest_sha256.lower(), "manifest_changed")
    migrate(target, apply=True)
    issued = finalize(target, manifest, manifest_sha256=digest(manifest),
                      authorization_reference=authorization_reference,
                      gate=RecognitionGate(capture=False, issuance=True))
    require(_explorer_rows(target) == before, "explorer_records_changed")
    with connection(target) as conn:
        require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "target_integrity_failed")
        require(conn.execute("PRAGMA foreign_key_check").fetchone() is None, "target_foreign_key_failed")
    require(file_hash(source) == source_sha256.lower(), "source_changed")
    require(file_hash(manifest_path) == manifest_sha256.lower(), "manifest_changed")
    result.update(mode="disposable_rehearsal", result=issued, source_unchanged=True,
                  explorer_unchanged=True, target_sha256=file_hash(target))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--manifest", dest="manifest_path", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--apply-disposable", action="store_true")
    parser.add_argument("--retry-existing", action="store_true")
    parser.add_argument("--authorization-reference")
    args = vars(parser.parse_args())
    try:
        print(canonical(run(**args)))
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as error:
        print(canonical({"ok": False, "production_authorized": False, "error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

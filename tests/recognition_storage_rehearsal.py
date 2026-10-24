"""Explicit disposable-only backup experiment. Never imported by the application.

Owns its backup directory and accepts only a registered, fresh execution fixture.
This is a rehearsal mechanism, not an installed production backup service.
"""

from contextlib import closing
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from uuid import UUID, uuid4

from src.review.recognition import administration as a, local_execution as c
from src.review.recognition.rules import canonical, digest


def utc(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError("UTC timestamp required")
    return result


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("backup integrity failure")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("backup foreign key failure")
        schema = conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        tables = [row[1] for row in schema if row[0] == "table"]
        # Ordered full content hashes detect missing rows, not just missing tables.
        content = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows = conn.execute("SELECT * FROM " + quoted).fetchall()
            content[table] = dict(count=len(rows), sha256=digest(sorted(canonical(row) for row in rows)))
        return dict(schema_sha256=digest(schema), tables=content)


class DisposableBackups:
    def __init__(self, context):
        if not c._production_fixture(context):
            raise ValueError("fresh production-format disposable fixture required")
        self.context = context
        self.config = c._context(context)["config"]
        self._temp = tempfile.TemporaryDirectory(prefix="recognition-backup-rehearsal-")
        self.root = Path(self._temp.name).resolve()

    def cleanup(self):
        self._temp.cleanup()

    def checked(self, directory):
        directory = Path(directory)
        if (directory.is_symlink() or directory.resolve().parent != self.root
                or directory.name != str(UUID(directory.name))):
            raise ValueError("backup path outside owned rehearsal root")
        for name in ("target.sqlite", "control.sqlite", "manifest.json"):
            path = directory / name
            if path.is_symlink() or (path.exists() and path.stat().st_nlink != 1):
                raise ValueError("backup alias rejected")
        return directory

    def create(self, *, now):
        utc(now)
        c._context(self.context)
        directory = self.checked(self.root / str(uuid4()))
        directory.mkdir(mode=0o700)
        # Same lock order as approval/execution. Separate read connections avoid
        # calling SQLite backup() on a connection with an active write transaction.
        with a.transaction(self.config, lock_target=True) as (_, _, binding):
            observations = {}
            for name, source in (("target", self.config.target), ("control", self.config.control)):
                with a.connect(source) as src, closing(sqlite3.connect(directory / (name + ".sqlite"))) as dst:
                    src.backup(dst)
                os.chmod(directory / (name + ".sqlite"), 0o600)
                observations[name] = inventory(directory / (name + ".sqlite"))
            manifest = dict(format="disposable-backup-rehearsal-v1", backup_id=directory.name,
                created_at_utc=now, retention_days=30, cadence="daily", generation=binding["generation"],
                installation_id=binding["installation_id"], target_id=binding["target_id"],
                inventories=observations,
                files={name: file_hash(directory / name) for name in ("target.sqlite", "control.sqlite")})
            (directory / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
            os.chmod(directory / "manifest.json", 0o600)
        self.verify(directory)
        return directory

    def verify(self, directory):
        directory = self.checked(directory)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if (manifest["format"] != "disposable-backup-rehearsal-v1"
                or manifest["backup_id"] != directory.name or manifest["retention_days"] != 30):
            raise ValueError("backup manifest mismatch")
        utc(manifest["created_at_utc"])
        for name in ("target", "control"):
            path = directory / (name + ".sqlite")
            if file_hash(path) != manifest["files"][path.name] or inventory(path) != manifest["inventories"][name]:
                raise ValueError("backup content mismatch")
        with a.connect(directory / "target.sqlite") as target, a.connect(directory / "control.sqlite") as control:
            a.schema.check_control(control)
            binding = a._binding(control)
            if (binding["generation"] != manifest["generation"]
                    or binding["installation_id"] != manifest["installation_id"]
                    or binding["target_id"] != manifest["target_id"]):
                raise ValueError("backup control binding mismatch")
            row = target.execute("SELECT installation_id,target_id FROM recognition_local_installation").fetchone()
            if tuple(row) != (binding["installation_id"], binding["target_id"]):
                raise ValueError("backup target binding mismatch")
            c.execution_schema.check_schema(target)
        return manifest

    def retention_plan(self, *, now):
        cutoff = utc(now) - timedelta(days=30)
        # Fail closed on unknown or damaged entries; never follow links.
        records = [(self.checked(path), self.verify(path)) for path in sorted(self.root.iterdir())]
        if not records:
            return []
        newest = max(records, key=lambda item: (utc(item[1]["created_at_utc"]), item[0].name))[0]
        return [path for path, body in records if path != newest and utc(body["created_at_utc"]) < cutoff]

    def retain(self, *, now):
        removed = []
        for directory in self.retention_plan(now=now):
            self.checked(directory)
            if {path.name for path in directory.iterdir()} != {"manifest.json", "target.sqlite", "control.sqlite"}:
                raise ValueError("unknown backup files; refusing removal")
            for name in ("target.sqlite", "control.sqlite", "manifest.json"):
                (directory / name).unlink()
            directory.rmdir()
            removed.append(directory.name)
        return removed

    def restore_target(self, directory):
        """Offline fixture restore only; surviving control is deliberately untouched.

        Operator must stop all readers/workers first. Refuse live WAL/journal
        artifacts; this is not an online restore protocol.
        """
        self.verify(directory)
        c._context(self.context)
        target = self.config.target
        if any(Path(str(path) + suffix).exists() for path in (target, self.config.control)
               for suffix in ("-wal", "-shm", "-journal")):
            raise ValueError("offline checkpoint and close required")
        replacement = target.parent / ("restore-" + str(uuid4()) + ".sqlite")
        try:
            with a.connect(directory / "target.sqlite") as src, closing(sqlite3.connect(replacement)) as dst:
                src.backup(dst)
            os.chmod(replacement, 0o600)
            if inventory(replacement) != self.verify(directory)["inventories"]["target"]:
                raise ValueError("restore verification failed")
            os.replace(replacement, target)
        finally:
            replacement.unlink(missing_ok=True)

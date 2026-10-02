"""Additive global-only migration; called only by the explicit offline command."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from .rules import RULE_KEY, canonical, digest, initial_definition


TABLES = {
    "recognition_rule_versions": """
        rule_key TEXT PRIMARY KEY NOT NULL, family TEXT NOT NULL CHECK(family='explorer'),
        version INTEGER NOT NULL CHECK(version>0), definition_json TEXT NOT NULL,
        definition_sha256 TEXT NOT NULL, created_at_utc TEXT NOT NULL,
        UNIQUE(family,version)""",
    "recognition_scopes": """
        scope_key TEXT PRIMARY KEY NOT NULL CHECK(scope_key='global'),
        kind TEXT NOT NULL CHECK(kind='global'), canonical_key TEXT NOT NULL UNIQUE CHECK(canonical_key='global'),
        label TEXT NOT NULL""",
    "recognition_completions": """
        assignment_id INTEGER PRIMARY KEY REFERENCES stop_review_assignments(id) ON DELETE NO ACTION,
        ledger_sequence INTEGER NOT NULL UNIQUE CHECK(ledger_sequence>0),
        observation_id INTEGER NOT NULL UNIQUE REFERENCES stop_observations(id) ON DELETE NO ACTION,
        reviewer_id INTEGER NOT NULL REFERENCES community_reviewers(id) ON DELETE NO ACTION,
        physical_stop_id INTEGER NOT NULL REFERENCES physical_stops(id) ON DELETE NO ACTION,
        completed_at_utc TEXT NOT NULL, original_completed_at TEXT NOT NULL,
        timestamp_provenance TEXT NOT NULL,
        qualification_rule_key TEXT NOT NULL REFERENCES recognition_rule_versions(rule_key) ON DELETE NO ACTION,
        origin TEXT NOT NULL CHECK(origin IN ('live','backfill')), recorded_at_utc TEXT NOT NULL""",
    "recognition_jobs": """
        assignment_id INTEGER PRIMARY KEY REFERENCES recognition_completions(assignment_id) ON DELETE NO ACTION,
        rule_key TEXT NOT NULL REFERENCES recognition_rule_versions(rule_key) ON DELETE NO ACTION,
        state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','leased','done','quarantined')),
        lease_token TEXT, lease_until_utc TEXT, attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0),
        last_error_code TEXT, updated_at_utc TEXT NOT NULL,
        CHECK((state='leased' AND lease_token IS NOT NULL AND lease_until_utc IS NOT NULL)
           OR (state<>'leased' AND lease_token IS NULL AND lease_until_utc IS NULL))""",
    "recognition_awards": """
        award_id TEXT PRIMARY KEY NOT NULL,
        reviewer_id INTEGER NOT NULL REFERENCES community_reviewers(id) ON DELETE NO ACTION,
        family TEXT NOT NULL CHECK(family='explorer'),
        scope_key TEXT NOT NULL REFERENCES recognition_scopes(scope_key) ON DELETE NO ACTION,
        tier_key TEXT NOT NULL, rule_key TEXT NOT NULL REFERENCES recognition_rule_versions(rule_key) ON DELETE NO ACTION,
        earned_at_utc TEXT NOT NULL, evaluated_at_utc TEXT NOT NULL,
        origin TEXT NOT NULL CHECK(origin IN ('live','backfill')),
        numerator INTEGER NOT NULL CHECK(numerator>0),
        evidence_json TEXT NOT NULL, evidence_sha256 TEXT NOT NULL,
        UNIQUE(reviewer_id,family,scope_key,tier_key)""",
    "recognition_award_witnesses": """
        award_id TEXT NOT NULL REFERENCES recognition_awards(award_id) ON DELETE NO ACTION,
        assignment_id INTEGER NOT NULL REFERENCES recognition_completions(assignment_id) ON DELETE NO ACTION,
        PRIMARY KEY(award_id,assignment_id)""",
    "recognition_runs": """
        run_id TEXT PRIMARY KEY NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('backfill','evaluation')),
        started_at_utc TEXT NOT NULL, finished_at_utc TEXT,
        manifest_json TEXT NOT NULL, manifest_sha256 TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('running','complete','failed')), summary_json TEXT,
        CHECK((state='running' AND finished_at_utc IS NULL) OR
              (state<>'running' AND finished_at_utc IS NOT NULL))""",
}


@contextmanager
def connection(database, *, write=False):
    """Never creates a mistyped database; owns rollback/close, not commit."""
    uri = Path(database).resolve().as_uri() + ("?mode=rw" if write else "?mode=ro")
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA recursive_triggers=ON")
        if not write:
            conn.execute("PRAGMA query_only=ON")
        yield conn
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


def install(conn):
    """Caller owns a transaction; never executescript/commit across its boundary."""
    if not conn.in_transaction or conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise ValueError("migration_requires_transaction_and_foreign_keys")
    required = {
        "community_reviewers": {"id"}, "physical_stops": {"id"},
        "stop_review_assignments": {"id", "stop_id", "reviewer_id", "status", "completed_at"},
        "stop_observations": {"id", "assignment_id", "physical_stop_id", "reviewer_id", "source"},
    }
    for table, columns in required.items():
        if not columns <= {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
            raise ValueError("incompatible_source_schema:" + table)
    for table, body in TABLES.items():
        sql = f"CREATE TABLE {table} ({body})"
        old = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if old and " ".join(old[0].split()) != " ".join(sql.split()):
            raise ValueError("incompatible_recognition_schema:" + table)
        if not old:
            conn.execute(sql)
    def ensure_object(kind, name, sql):
        old = conn.execute("SELECT sql FROM sqlite_master WHERE type=? AND name=?", (kind, name)).fetchone()
        if old and " ".join(old[0].split()) != " ".join(sql.split()):
            raise ValueError("incompatible_recognition_schema:" + name)
        if not old:
            conn.execute(sql)

    for table in sorted(TABLES.keys() - {"recognition_jobs", "recognition_runs"}):
        for action in ("UPDATE", "DELETE"):
            name = f"{table}_immutable_{action.lower()}"
            ensure_object("trigger", name, f"""CREATE TRIGGER {name}
                BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_recognition_evidence'); END""")
        # REPLACE's implicit DELETE bypasses delete triggers on legacy connections
        # with recursive_triggers=OFF. Block conflicting INSERTs as well.
        keys = {
            "recognition_rule_versions": "rule_key=NEW.rule_key OR (family=NEW.family AND version=NEW.version)",
            "recognition_scopes": "scope_key=NEW.scope_key OR canonical_key=NEW.canonical_key",
            "recognition_completions": "assignment_id=NEW.assignment_id OR observation_id=NEW.observation_id",
            "recognition_awards": "award_id=NEW.award_id OR (reviewer_id=NEW.reviewer_id AND family=NEW.family AND scope_key=NEW.scope_key AND tier_key=NEW.tier_key)",
            "recognition_award_witnesses": "award_id=NEW.award_id AND assignment_id=NEW.assignment_id",
        }
        name = f"{table}_immutable_replace"
        ensure_object("trigger", name, f"""CREATE TRIGGER {name} BEFORE INSERT ON {table}
            WHEN EXISTS(SELECT 1 FROM {table} WHERE {keys[table]})
            BEGIN SELECT RAISE(ABORT,'immutable_recognition_evidence'); END""")
    ensure_object("trigger", "recognition_jobs_context", """CREATE TRIGGER recognition_jobs_context
        BEFORE UPDATE OF assignment_id,rule_key ON recognition_jobs
        BEGIN SELECT RAISE(ABORT,'immutable_job_context'); END""")
    ensure_object("trigger", "recognition_completion_sequence", """CREATE TRIGGER recognition_completion_sequence
        BEFORE INSERT ON recognition_completions
        WHEN NEW.ledger_sequence<>(SELECT COALESCE(MAX(ledger_sequence),0)+1 FROM recognition_completions)
        BEGIN SELECT RAISE(ABORT,'invalid_completion_sequence'); END""")
    ensure_object("trigger", "recognition_jobs_replace", """CREATE TRIGGER recognition_jobs_replace
        BEFORE INSERT ON recognition_jobs WHEN EXISTS(SELECT 1 FROM recognition_jobs WHERE assignment_id=NEW.assignment_id)
        BEGIN SELECT RAISE(ABORT,'existing_recognition_job'); END""")
    for action in ("UPDATE", "DELETE"):
        name = f"recognition_runs_final_{action.lower()}"
        ensure_object("trigger", name, f"""CREATE TRIGGER {name}
            BEFORE {action} ON recognition_runs WHEN OLD.state<>'running'
            BEGIN SELECT RAISE(ABORT,'finalized_recognition_run'); END""")
    ensure_object("trigger", "recognition_runs_replace", """CREATE TRIGGER recognition_runs_replace
        BEFORE INSERT ON recognition_runs WHEN EXISTS(SELECT 1 FROM recognition_runs WHERE run_id=NEW.run_id)
        BEGIN SELECT RAISE(ABORT,'existing_recognition_run'); END""")
    for name, table, columns in (
        ("owner_stop", "completions", "reviewer_id,physical_stop_id,completed_at_utc,assignment_id"),
        ("time", "completions", "completed_at_utc,assignment_id"),
        ("stop_time", "completions", "physical_stop_id,completed_at_utc,assignment_id"),
        ("pending", "jobs", "state,lease_until_utc,assignment_id"),
        ("owner_time", "awards", "reviewer_id,earned_at_utc,award_id"),
    ):
        index = f"recognition_{table}_{name}"
        ensure_object("index", index, f"CREATE INDEX {index} ON recognition_{table}({columns})")
    definition = initial_definition()
    row = conn.execute("SELECT definition_json,definition_sha256,family,version FROM recognition_rule_versions WHERE rule_key=?", (RULE_KEY,)).fetchone()
    if row and tuple(row) != (canonical(definition), digest(definition), "explorer", 1):
        raise ValueError("initial_rule_conflict")
    if not row:
        conn.execute("INSERT INTO recognition_rule_versions VALUES(?, 'explorer',1,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
                     (RULE_KEY, canonical(definition), digest(definition)))
    conn.execute("INSERT INTO recognition_scopes SELECT 'global','global','global','Global' WHERE NOT EXISTS (SELECT 1 FROM recognition_scopes WHERE scope_key='global')")


def migrate(database, *, apply=False):
    if not apply:
        with connection(database) as source:
            rehearsal = sqlite3.connect(":memory:")
            try:
                source.backup(rehearsal)
                rehearsal.execute("PRAGMA foreign_keys=ON")
                rehearsal.execute("BEGIN")
                install(rehearsal)
                if rehearsal.execute("PRAGMA foreign_key_check").fetchone():
                    raise ValueError("foreign_key_check_failed")
            finally:
                rehearsal.close()
        return
    with connection(database, write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")
        install(conn)
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("foreign_key_check_failed")
        conn.commit()

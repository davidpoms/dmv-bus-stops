"""Test-only issuance into a new, isolated disposable file; never production."""

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.active.rehearse_recognition_capture import (
    application_fingerprint, check_schema, check_state, file_hash, offline_file,
    read_manifest, require,
)
from src.review.recognition import RecognitionGate
from src.review.recognition.backfill import source_plan
from src.review.recognition.integrity import check_award_integrity
from src.review.recognition.processing import lease_jobs, prepare_evaluation, finalize_job
from src.review.recognition.rules import RULE_KEY, canonical, digest
from src.review.recognition.schema import connection

OUTPUT_ROOT = ROOT / '.tmp' / 'explorer-issuance-rehearsals'
PAIRS = [(158, '5'), (160, '5'), (169, '5'), (169, '20')]


def validate_input(conn, manifest):
    check_schema(conn, additional_written_tables={'recognition_awards', 'recognition_award_witnesses'})
    require([r[0] for r in conn.execute('PRAGMA integrity_check')] == ['ok'], 'integrity_failed')
    check_state(conn, dict(manifest, candidates=[]), allow_empty=False)
    require(conn.execute('SELECT COUNT(*) FROM recognition_rule_versions').fetchone()[0] == 1
            and conn.execute('SELECT COUNT(*) FROM recognition_scopes').fetchone()[0] == 1,
            'unexpected_rules_or_scopes')
    plan = source_plan(conn, RULE_KEY, after_assignment=141, through_assignment=210,
                       limit=manifest['cohort']['limit'],
                       sqlite_utc_provenance=manifest['sqlite_utc_provenance'])
    require(all(canonical(v) == canonical(manifest[k]) for k, v in plan.items()),
            'source_manifest_mismatch')


def evaluate(database, manifest):
    owners = sorted({f['reviewer_id'] for f in manifest['qualified']})
    prepared = {owner: prepare_evaluation(database, owner, RULE_KEY) for owner in owners}
    actual = [c for owner in owners for c in json.loads(prepared[owner].candidates_json)]
    require(canonical(actual) == canonical(manifest['candidates']), 'candidate_set_mismatch')
    return prepared


def postcheck(conn, manifest):
    awards = [dict(r) for r in conn.execute('SELECT * FROM recognition_awards ORDER BY award_id')]
    expected = {digest(tuple(c[k] for k in ('reviewer_id', 'family', 'scope_key', 'tier_key'))): c
                for c in manifest['candidates']}
    require({a['award_id'] for a in awards} == set(expected) and len(awards) == 4,
            'unexpected_awards')
    for award in awards:
        candidate = expected[award['award_id']]
        require(all(award[k] == v for k, v in candidate.items() if k != 'evidence')
                and award['evidence_json'] == canonical(candidate['evidence'])
                and award['origin'] == 'backfill', 'award_manifest_mismatch')
        check_award_integrity(conn, award['award_id'])
    require(tuple(conn.execute('SELECT COUNT(*),COUNT(DISTINCT assignment_id) '
                               'FROM recognition_award_witnesses').fetchone()) == (35, 30),
            'unexpected_witness_coverage')
    jobs = [dict(r) for r in conn.execute('SELECT * FROM recognition_jobs ORDER BY assignment_id')]
    require([j['assignment_id'] for j in jobs] == [f['assignment_id'] for f in manifest['qualified']]
            and all(j['state'] == 'done' and j['attempts'] == 1 and j['lease_token'] is None
                    and j['lease_until_utc'] is None and j['last_error_code'] is None
                    and j['rule_key'] == RULE_KEY for j in jobs), 'unexpected_final_jobs')
    require([r[0] for r in conn.execute('PRAGMA integrity_check')] == ['ok']
            and not conn.execute('PRAGMA foreign_key_check').fetchall(), 'final_integrity_failed')
    return {'awards': 4, 'witness_rows': 35, 'unique_witness_assignments': 30,
            'done_jobs': len(jobs), 'integrity': 'ok'}


def api_check(target, manifest):
    """Flask test client only; credentials never leave memory or enter output."""
    from src.api import app as api
    fields = ('family', 'scope_key', 'tier_key', 'numerator', 'earned_at_utc')
    with connection(target) as conn:
        owners = [tuple(r) for r in conn.execute(
            'SELECT id,reviewer_key FROM community_reviewers ORDER BY id')]
    old = {k: api.app.config[k] for k in ('TESTING', 'SECRET_KEY')}
    real_connect = sqlite3.connect

    def readonly(database, *args, **kwargs):
        require(str(database) == target.as_uri() + '?mode=ro', 'api_database_not_readonly_target')
        conn = real_connect(database, *args, **kwargs)
        conn.execute('PRAGMA query_only=1')
        return conn

    try:
        api.app.config.update(TESTING=True, SECRET_KEY='disposable-rehearsal-only')
        with patch.object(api, 'DATABASE_PATH', target), patch.object(sqlite3, 'connect', readonly):
            client = api.app.test_client()
            response = client.get('/api/reviewer/achievements')
            require(response.status_code == 401 and response.headers['Cache-Control'] == 'private, no-store',
                    'api_privacy_failed')
            total = 0
            for owner, key in owners:
                with client.session_transaction() as session:
                    session['authenticated_reviewer_id'] = owner
                    session['reviewer_key'] = key
                response = client.get('/api/reviewer/achievements')
                expected = [{k: c[k] for k in fields} for c in sorted(
                    (c for c in manifest['candidates'] if c['reviewer_id'] == owner),
                    key=lambda c: (c['earned_at_utc'], digest(tuple(c[k] for k in
                                  ('reviewer_id', 'family', 'scope_key', 'tier_key')))))]
                require(response.status_code == 200 and response.headers['Cache-Control'] == 'private, no-store'
                        and response.get_json() == {'available': True, 'achievements': expected},
                        'api_awards_mismatch')
                total += len(expected)
            require(total == 4, 'api_award_count')
    finally:
        api.app.config.update(old)
    return {'authenticated_awards': total, 'unauthenticated_status': 401, 'network_server': False}


def rehearse(source_db, manifest_path, destination, *, source_sha256, manifest_sha256,
             test_only=False):
    require(test_only is True, 'explicit_test_only_required')
    source = offline_file(source_db)
    require(file_hash(source) == source_sha256.lower(), 'source_hash_mismatch')
    manifest_path = Path(manifest_path).resolve(strict=True)
    manifest = read_manifest(manifest_path, manifest_sha256, 55, 14, expected_candidates=4)
    require([(c['reviewer_id'], c['tier_key']) for c in manifest['candidates']] == PAIRS,
            'reviewed_candidate_identities_required')
    require(manifest['cohort']['after_assignment'] == 141
            and manifest['cohort']['through_assignment'] == 210, 'wrong_cohort')
    target = Path(destination).resolve()
    require(target != source, 'source_target_alias')
    require(target.parent == OUTPUT_ROOT.resolve() and not OUTPUT_ROOT.is_symlink()
            and OUTPUT_ROOT.resolve() == Path(os.path.abspath(OUTPUT_ROOT))
            and target.name.startswith('disposable-') and target.suffix == '.db',
            'reserved_disposable_destination_required')
    require(not target.exists() and not any(Path(str(target) + s).exists()
            for s in ('-wal', '-shm', '-journal')), 'destination_exists')
    protected = [ROOT / 'src/database/dmv_bus_stops.db']
    if os.environ.get('DMV_BUS_STOPS_DB'):
        protected.append(Path(os.environ['DMV_BUS_STOPS_DB']))
    require(all(target != p.resolve() for p in protected), 'application_target_forbidden')
    with connection(source) as conn:
        conn.execute('BEGIN')
        validate_input(conn, manifest)
        app_before = application_fingerprint(conn)
        immutable = {t: [dict(r) for r in conn.execute('SELECT * FROM ' + t)] for t in
                     ('recognition_completions', 'recognition_rule_versions', 'recognition_scopes', 'recognition_runs')}
    evaluate(source, manifest)
    require(file_hash(source) == source_sha256.lower(), 'source_changed_before_copy')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Exclusive creation: never overwrite a file or follow an existing target link.
        with source.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        require(not source.samefile(target) and file_hash(target) == source_sha256.lower(), 'copy_mismatch')
        identity = (target.stat().st_dev, target.stat().st_ino)
        with connection(target) as conn:
            conn.execute('BEGIN')
            validate_input(conn, manifest)
        prepared = evaluate(target, manifest)
        require(file_hash(manifest_path) == manifest_sha256.lower()
                and file_hash(source) == source_sha256.lower(), 'inputs_changed')
        require((target.stat().st_dev, target.stat().st_ino) == identity, 'target_replaced')
        gate = RecognitionGate(capture=False, issuance=True)
        with connection(target, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            validate_input(conn, manifest)
            require(application_fingerprint(conn) == app_before, 'application_data_changed')
            for table, rows in immutable.items():
                require([dict(r) for r in conn.execute('SELECT * FROM ' + table)] == rows, 'immutable_data_changed')
            jobs = lease_jobs(conn, RULE_KEY, gate=gate, limit=55)
            require([j['assignment_id'] for j in jobs] == [f['assignment_id'] for f in manifest['qualified']],
                    'unexpected_leases')
            owners = {f['assignment_id']: f['reviewer_id'] for f in manifest['qualified']}
            for job in jobs:
                finalize_job(conn, job['assignment_id'], job['lease_token'], RULE_KEY,
                             prepared[owners[job['assignment_id']]], gate=gate)
            result = postcheck(conn, manifest)
            require(application_fingerprint(conn) == app_before, 'application_data_changed')
            for table, rows in immutable.items():
                require([dict(r) for r in conn.execute('SELECT * FROM ' + table)] == rows, 'immutable_data_changed')
            conn.commit()
        issued_hash = file_hash(target)
        # Retry the service workflow: completed jobs must not be leased again.
        evaluate(target, manifest)
        with connection(target, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            require(lease_jobs(conn, RULE_KEY, gate=gate, limit=55) == [], 'retry_created_leases')
            postcheck(conn, manifest)
            conn.commit()
        require(file_hash(target) == issued_hash, 'retry_changed_database')
        api_result = api_check(target, manifest)
        require(file_hash(target) == issued_hash, 'api_changed_database')
        return dict(result, mode='test-only-disposable', destination=str(target), target_sha256=issued_hash,
                    source_sha256=source_sha256.lower(), manifest_sha256=manifest_sha256.lower(),
                    retry_unchanged=True, api=api_result)
    finally:
        require(file_hash(source) == source_sha256.lower(), 'source_changed')
        with connection(source) as conn:
            conn.execute('BEGIN')
            validate_input(conn, manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-only', action='store_true', required=True)
    for name in ('source-db', 'manifest', 'destination', 'source-sha256', 'manifest-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    # No network calls are permitted, including accidental calls from API imports.
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('network_forbidden')), \
         patch.object(socket, 'create_connection', side_effect=RuntimeError('network_forbidden')):
        try:
            print(canonical(rehearse(args.source_db, args.manifest, args.destination,
                  source_sha256=args.source_sha256, manifest_sha256=args.manifest_sha256,
                  test_only=args.test_only)))
        except (ValueError, OSError, sqlite3.Error) as error:
            print(canonical({'status': 'failed', 'error': str(error), 'destination': args.destination}), file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

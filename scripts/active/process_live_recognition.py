"""Explicit pending-job processor; read-only verification unless --issue is supplied."""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.review.recognition import DISABLED, RecognitionGate
from src.review.recognition.processing import bounded, lease_jobs, prepare_evaluation, finalize_job
from src.review.recognition.qualification import Quarantined
from src.review.recognition.rules import canonical, load_rule
from src.review.recognition.schema import connection


def counts(conn, rule_key):
    result = dict(pending=0, leased=0, done=0, quarantined=0)
    result.update(dict(conn.execute(
        'SELECT state,COUNT(*) FROM recognition_jobs WHERE rule_key=? GROUP BY state', (rule_key,))))
    return result


def process(database, rule_key, *, limit=25, issue=False, gate=DISABLED):
    """Process a fixed pending cohort, with at most two stale-snapshot retries per job.

    Lease and finalize commit together. Failed attempts roll back their lease;
    other workers may win a pending job between retries, in which case it is skipped.
    Quarantines remain visible in both the job table and the JSON report.
    """
    bounded(limit)
    database = Path(database).resolve()
    if not database.is_file():
        raise ValueError('database_must_be_existing_file')
    if issue and not gate.issuance:
        raise ValueError('issuance_disabled')
    with connection(database) as conn:
        conn.execute('BEGIN')
        load_rule(conn, rule_key)
        jobs = conn.execute('''SELECT j.assignment_id,c.reviewer_id FROM recognition_jobs j
            JOIN recognition_completions c USING(assignment_id)
            WHERE j.rule_key=? AND j.state='pending' ORDER BY j.assignment_id LIMIT ?''',
            (rule_key, limit)).fetchall()
        initial = counts(conn, rule_key)
    result = dict(rule_key=rule_key, database=str(database), mode='issue' if issue else 'verify-only',
                  jobs_found=len(jobs), jobs_attempted=0, jobs_completed=0, awards_issued=0,
                  jobs_skipped=0, stale_retries=0, quarantined_jobs=[], error_jobs=[],
                  final_counts=initial)
    if not issue:
        return result
    prepared = {}
    for assignment_id, reviewer_id in jobs:
        result['jobs_attempted'] += 1
        for attempt in range(3):
            try:
                if reviewer_id not in prepared:
                    prepared[reviewer_id] = prepare_evaluation(database, reviewer_id, rule_key)
                with connection(database, write=True) as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    leased = lease_jobs(conn, rule_key, gate=gate, limit=1,
                                        pending_assignment_id=assignment_id)
                    if not leased:
                        result['jobs_skipped'] += 1
                        break
                    before = conn.execute('SELECT COUNT(*) FROM recognition_awards WHERE reviewer_id=?',
                                          (reviewer_id,)).fetchone()[0]
                    finalize_job(conn, assignment_id, leased[0]['lease_token'], rule_key,
                                 prepared[reviewer_id], gate=gate)
                    issued = conn.execute('SELECT COUNT(*) FROM recognition_awards WHERE reviewer_id=?',
                                          (reviewer_id,)).fetchone()[0] - before
                    conn.commit()
                result['jobs_completed'] += 1
                result['awards_issued'] += issued
                break
            except Quarantined as error:
                code = str(error)
                if code == 'stale_or_invalid_candidates' and attempt < 2:
                    prepared.pop(reviewer_id, None)
                    result['stale_retries'] += 1
                    continue
                with connection(database, write=True) as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    conn.execute('''UPDATE recognition_jobs SET state='quarantined',last_error_code=?,
                        updated_at_utc=strftime('%Y-%m-%dT%H:%M:%SZ','now')
                        WHERE assignment_id=? AND rule_key=? AND state='pending' ''',
                        (code, assignment_id, rule_key))
                    conn.commit()
                result['quarantined_jobs'].append(dict(assignment_id=assignment_id, code=code))
                break
            except (sqlite3.Error, ValueError) as error:
                # Do not expose exception messages, which may contain source payloads.
                result['error_jobs'].append(dict(assignment_id=assignment_id, code=type(error).__name__))
                break
    with connection(database) as conn:
        result['final_counts'] = counts(conn, rule_key)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--rule-key', required=True)
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--issue', action='store_true', help='Explicitly authorize award issuance')
    args = parser.parse_args(argv)
    try:
        result = process(args.db, args.rule_key, limit=args.limit, issue=args.issue,
                         gate=RecognitionGate(capture=False, issuance=True) if args.issue else DISABLED)
    except (sqlite3.Error, ValueError) as error:
        print(canonical(dict(error=type(error).__name__, code='recognition_processing_failed')))
        return 1
    print(canonical(result))
    return int(bool(result['quarantined_jobs'] or result['error_jobs']))


if __name__ == '__main__':
    raise SystemExit(main())

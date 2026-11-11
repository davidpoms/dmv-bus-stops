"""Z31: in-memory DDL and detached synthetic DATA, never a runtime database."""

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import runtime_decision_outcome_journal_schema as s
from src.review.recognition.rules import canonical, digest
from tests.test_recognition_runtime_target_entry_storage import graph


def data():
    _, sources = graph()
    physical = sources['authority_body']['physical_snapshot']
    physical['target']['observation']['database'] = str(Path(__file__).resolve().parent / 'synthetic-target.db')
    physical['control_identity']['database'] = str(Path(__file__).resolve().parent / 'synthetic-control.db')
    decision = dict(format=s.DECISION_FORMAT, authority=sources['authority_body'],
                    recorded_at_utc='2099-01-01T00:00:00Z')
    genesis = s._genesis(decision)
    pending = dict(genesis, sequence=2, state='TARGET_PENDING', previous_sha256=digest(genesis))
    witness = dict(format=s.WITNESS_FORMAT, decision=decision, pending=pending,
                   recorded_at_utc='2099-01-01T00:00:01Z', outcome='TARGET_COMMITTED',
                   effect_evidence_sha256='a'*64)
    return decision, genesis, pending, witness


def projection(value, side):
    decision = value if side == 'control' else value['decision']
    body = decision['authority']
    row = dict(authority_id=body['authority_id'], authority_sha256=digest(body),
               installation_id=body['runtime_target']['installation_id'], target_id=body['runtime_target']['target_id'],
               operation_id=body['operation_reference']['operation_id'],
               operation_sha256=body['operation_reference']['operation_sha256'],
               writer_manifest_sha256=body['operation_reference']['writer_manifest_sha256'],
               recorded_at=s._time(value['recorded_at_utc']), body_json=canonical(value), body_sha256=digest(value))
    if side == 'target':
        row.update(pending_sha256=digest(value['pending']), effect_evidence_sha256=value['effect_evidence_sha256'])
    return row


def insert(conn, table, row, replace=False):
    conn.execute(f"INSERT {'OR REPLACE ' if replace else ''}INTO {table} ({','.join(row)}) "
                 f"VALUES ({','.join('?' for _ in row)})", tuple(row.values()))


def event_row(value):
    return dict(authority_id=value['authority_id'], authority_sha256=value['authority_sha256'],
                sequence=value['sequence'], state=value['state'], at=s._time(value['at_utc']),
                previous_sha256=value['previous_sha256'], body_json=canonical(value), body_sha256=digest(value))


class JournalSchemaTests(unittest.TestCase):
    def setUp(self):
        self.d, self.g, self.p, self.w = data()

    def database(self, side):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        self.addCleanup(conn.close)
        for sql in s.definitions(side).values():
            conn.execute(sql)
        return conn

    def test_definitions_are_deterministic_and_inert(self):
        with patch.object(sqlite3, 'connect', side_effect=AssertionError('not inert')):
            for side in ('control', 'target'):
                self.assertEqual(s.definitions(side), s.definitions(side))
        self.assertFalse(any(hasattr(s, name) for name in ('install', 'migrate', 'execute', 'issue', 'acquire')))

    def test_partial_or_extended_package_rejected(self):
        conn = self.database('control')
        conn.execute(f'DROP TRIGGER {s.HISTORY}_immutable_delete')
        with self.assertRaises(ValueError):
            s.inspect_rows(conn, 'control')
        target = self.database('target')
        target.execute(f'CREATE TRIGGER extra_witness_trigger AFTER INSERT ON {s.WITNESSES} BEGIN SELECT 1; END')
        with self.assertRaises(ValueError):
            s.inspect_rows(target, 'target')

    def test_round_trips_and_lossless_physical_integers(self):
        self.assertEqual(self.d, s.parse_decision(s.encode_decision(self.d), expected_sha256=digest(self.d)))
        self.assertEqual(self.w, s.parse_witness(s.encode_witness(self.w), expected_sha256=digest(self.w)))
        self.assertEqual(2**80, self.w['decision']['authority']['physical_snapshot']['target']['observation']['device'])
        for value, previous in ((self.g, None), (self.p, self.g)):
            self.assertEqual(value, s.parse_event(s.encode_event(value, decision=self.d, previous=previous),
                                                 expected_sha256=digest(value), decision=self.d, previous=previous))

    def test_codec_malformed_values_and_no_reservation_metadata(self):
        cases = [('format', 'unknown'), ('recorded_at_utc', '2099-01-01T00:00:00.0Z'),
                 ('recorded_at_utc', True), ('pid', 123)]
        for key, val in cases:
            value = deepcopy(self.d); value[key] = val
            with self.subTest(key=key, val=val), self.assertRaises((ValueError, TypeError)):
                s.validate_decision(value)
        for key, bad in (('authority_id', 'A'*36), ('authority_id', self.d['authority']['authority_id']+'\0'),
                         ('expires_at_utc', '2099-01-01T00:02:01Z')):
            value = deepcopy(self.d); value['authority'][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                s.validate_decision(value)
        for bad in ('A'*64, 'a'*64+'\0', 'a'*20+'\0'+'a'*43, 1, True, 1.0):
            value = deepcopy(self.w); value['effect_evidence_sha256'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                s.validate_witness(value)

    def test_noncanonical_json_duplicate_keys_and_wrong_digest(self):
        for raw in (json.dumps(self.d), canonical(self.d)[:-1]+',"format":"'+s.DECISION_FORMAT+'"}'):
            with self.assertRaises(ValueError):
                s.parse_decision(raw, expected_sha256=digest(self.d))
        with self.assertRaises(ValueError):
            s.parse_witness(canonical(self.w), expected_sha256='b'*64)

    def test_transitions_terminal_uncertain_and_completed(self):
        uncertain = dict(self.p, sequence=3, state='TARGET_UNCERTAIN', previous_sha256=digest(self.p),
                         evidence=dict(pending_sha256=digest(self.p), classification='COMMIT_UNCONFIRMED'))
        s.validate_event(uncertain, decision=self.d, previous=self.p, pending=self.p)
        for state, evidence in (
                ('TARGET_FAILED', dict(pending_sha256=digest(self.p), no_commit_evidence_sha256='c'*64)),
                ('COMPLETED', dict(pending_sha256=digest(self.p), witness_sha256=digest(self.w)))):
            terminal = dict(uncertain, sequence=4, state=state, at_utc=self.w['recorded_at_utc'],
                            previous_sha256=digest(uncertain), evidence=evidence)
            s.validate_event(terminal, decision=self.d, previous=uncertain, pending=self.p, witness=self.w)
            with self.assertRaises(ValueError):
                s.validate_event(dict(terminal, sequence=5), decision=self.d, previous=terminal, pending=self.p, witness=self.w)
        for change in (dict(sequence=True), dict(sequence=2.0), dict(state='CONTROL_COMMITTED'),
                       dict(state='TARGET_PENDING', retry_authorized=True), dict(previous_sha256='0'*64)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                s.validate_event(dict(uncertain, **change), decision=self.d, previous=self.p, pending=self.p)

    def test_witness_cannot_substitute_scope_pending_or_deadline(self):
        for mutate in (lambda v: v['pending'].update(authority_id='00000000-0000-0000-0000-000000000000'),
                       lambda v: v.update(outcome='TARGET_FAILED'),
                       lambda v: v.update(recorded_at_utc='2099-01-01T00:02:00Z'),
                       lambda v: v['pending'].update(previous_sha256='b'*64)):
            value = deepcopy(self.w); mutate(value)
            with self.assertRaises(ValueError):
                s.validate_witness(value)

    def test_in_memory_control_and_target_inspection_is_read_only(self):
        control, target = self.database('control'), self.database('target')
        insert(control, s.DECISIONS, projection(self.d, 'control'))
        for value in (self.g, self.p):
            insert(control, s.HISTORY, event_row(value))
        insert(target, s.WITNESSES, projection(self.w, 'target'))
        for conn, side in ((control, 'control'), (target, 'target')):
            before = conn.total_changes
            conn.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY if action in
                                (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            self.assertEqual(dict(decisions=1, execution_authority=False, retry_authorized=False), s.inspect_rows(conn, side))
            self.assertEqual(before, conn.total_changes)

    def test_update_delete_replace_and_unique_fences_both_placements(self):
        for side, table, value in (('control', s.DECISIONS, self.d), ('target', s.WITNESSES, self.w)):
            conn = self.database(side); row = projection(value, side); insert(conn, table, row)
            for sql in (f'UPDATE {table} SET recorded_at=recorded_at', f'DELETE FROM {table}'):
                with self.subTest(side=side, sql=sql), self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(sql)
            for recursive in ('OFF', 'ON'):
                conn.execute('PRAGMA recursive_triggers='+recursive)
                with self.assertRaises(sqlite3.IntegrityError):
                    insert(conn, table, row, replace=True)
            # A different decision ID cannot evade operation/manifest uniqueness.
            other_value = deepcopy(value)
            other_source = other_value['authority'] if side == 'control' else other_value['decision']['authority']
            other_source['authority_id'] = '00000000-0000-0000-0000-000000000001'
            other = projection(other_value, side)
            with self.assertRaises(sqlite3.IntegrityError):
                insert(conn, table, other)

    def test_sql_projection_transition_fk_and_immutability_guards(self):
        conn = self.database('control')
        with self.assertRaises(sqlite3.IntegrityError):
            insert(conn, s.HISTORY, event_row(self.g))
        insert(conn, s.DECISIONS, projection(self.d, 'control'))
        with self.assertRaises(sqlite3.IntegrityError):
            insert(conn, s.HISTORY, event_row(self.p))
        insert(conn, s.HISTORY, event_row(self.g))
        insert(conn, s.HISTORY, event_row(self.p))
        for sql in (f'UPDATE {s.HISTORY} SET at=at', f'DELETE FROM {s.HISTORY}'):
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(sql)
        with self.assertRaises(sqlite3.IntegrityError):
            insert(conn, s.HISTORY, event_row(self.p), replace=True)
        bad = dict(self.p, sequence=3, previous_sha256=digest(self.p))
        with self.assertRaises(sqlite3.IntegrityError):
            insert(conn, s.HISTORY, event_row(bad))
        for bad in ('a'*64+'\0', 'A'*64):
            fresh = self.database('control')  # No collision may mask the CHECK failure.
            row = projection(self.d, 'control'); row['authority_sha256'] = bad
            with self.assertRaises(sqlite3.IntegrityError):
                insert(fresh, s.DECISIONS, row)

    def test_uncertain_and_failed_graphs_do_not_restore_start(self):
        conn = self.database('control')
        insert(conn, s.DECISIONS, projection(self.d, 'control'))
        uncertain = dict(self.p, sequence=3, state='TARGET_UNCERTAIN', previous_sha256=digest(self.p),
                         evidence=dict(pending_sha256=digest(self.p), classification='CONNECTION_FAILURE'))
        failed = dict(uncertain, sequence=4, state='TARGET_FAILED', previous_sha256=digest(uncertain),
                      evidence=dict(pending_sha256=digest(self.p), no_commit_evidence_sha256='f'*64))
        for value in (self.g, self.p, uncertain, failed):
            insert(conn, s.HISTORY, event_row(value))
            self.assertFalse(s.inspect_rows(conn, 'control')['retry_authorized'])
        with self.assertRaises(sqlite3.IntegrityError):
            insert(conn, s.HISTORY, event_row(dict(self.p, sequence=5, previous_sha256=digest(failed))))

    def test_row_inspection_rejects_tampered_digest_and_witness_projection(self):
        conn = self.database('target')
        row = projection(self.w, 'target'); row['pending_sha256'] = 'f'*64
        insert(conn, s.WITNESSES, row)
        with self.assertRaises(ValueError):
            s.inspect_rows(conn, 'target')
        fresh = self.database('target')
        row = projection(self.w, 'target'); row['body_sha256'] = 'f'*64
        insert(fresh, s.WITNESSES, row)
        with self.assertRaises(ValueError):
            s.inspect_rows(fresh, 'target')

    def test_crash_prefixes_and_completed_requires_target_data(self):
        conn = self.database('control')
        insert(conn, s.DECISIONS, projection(self.d, 'control'))
        with self.assertRaises(ValueError):
            s.inspect_rows(conn, 'control')  # Partial registration is not a valid graph.
        for value in (self.g, self.p):
            insert(conn, s.HISTORY, event_row(value))
            s.inspect_rows(conn, 'control')
        completed = dict(self.p, sequence=3, state='COMPLETED', at_utc=self.w['recorded_at_utc'],
                         previous_sha256=digest(self.p),
                         evidence=dict(pending_sha256=digest(self.p), witness_sha256=digest(self.w)))
        insert(conn, s.HISTORY, event_row(completed))
        with self.assertRaises(ValueError):
            s.inspect_rows(conn, 'control')
        result = s.inspect_rows(conn, 'control', witnesses={completed['authority_id']: self.w})
        self.assertFalse(result['execution_authority'])
        self.assertFalse(result['retry_authorized'])

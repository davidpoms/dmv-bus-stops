"""4b-1 codecs/fences; all graph/ACK inserts below are disposable fixtures only."""

from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4
import json
import unittest

from src.review.recognition import administration as a, events, operations, operation_schema
from src.review.recognition import runtime_proposal_records as records, runtime_validation as runtime
from src.review.recognition import runtime_scope_validation as scope, runtime_operation_contract as contract
from src.review.recognition import production_operations, approvals, local_execution, local_readiness, writer_boundary
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_operation_contract as lifecycle
from tests import test_recognition_administration as f


class RuntimeProposalRecordTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lifecycle.RuntimeOperationContractTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        self.primary, self.session = self.fixture.primary, self.fixture.session
        self.frozen = deepcopy(self.fixture.frozen)
        with runtime.authentication_transaction(self.config) as context:
            self.operation = self.fixture.build(context)
            head = a._audit_head(runtime._contexts[context]['control'])
            self.ack = records.build_acknowledgement(self.operation, context=context, frozen=self.frozen,
                operation_sha256=digest(self.operation), acknowledged_at_utc=f.at(900),
                previous_sha256=head['body_sha256'])

    def compare(self, operation=None, ack=None):
        operation = self.operation if operation is None else operation
        ack = self.ack if ack is None else ack
        with runtime.authentication_transaction(self.config) as context:
            return records.match_acknowledgement(operation, context=context, frozen=self.frozen,
                operation_sha256=digest(operation), acknowledgement=ack, acknowledgement_sha256=digest(ack))

    def read(self, operation_id=None):
        with runtime.authentication_transaction(self.config) as context:
            return records.read_acknowledged_proposal(context, operation_id or self.operation['operation_id'],
                session_token=self.session, primary_token=self.primary)

    def snapshot(self):
        return self.config.control.read_bytes(), self.config.target.read_bytes()

    def insert_graph_fixture(self, operation=None, frozen=None):
        operation = self.operation if operation is None else operation
        frozen = self.frozen if frozen is None else frozen
        p, e = frozen['preparation'], frozen['event']
        with a.connect(self.config.target, write=True) as target:
            target.execute('BEGIN IMMEDIATE')
            events._insert(target, 'recognition_preparations', 'preparation_id,parent_event_id',
                (p['preparation_id'], p['request']['parent_event_id']), p)
            events._insert(target, 'recognition_frozen_events', 'event_id,preparation_id',
                (e['event_id'], p['preparation_id']), e)
            item = dict(event_id=e['event_id'], sequence=1, state='READY', reason='test-only frozen graph',
                        recorded_at_utc=e['frozen_at_utc'], previous_sha256=None)
            events._insert(target, 'recognition_event_history', 'event_id,sequence', (e['event_id'], 1), item)
            events._insert(target, 'recognition_operation_contracts', 'operation_id,event_id',
                (operation['operation_id'], e['event_id']), operation)
            for kind, state in (('decisions', 'PREPARED'), ('executions', 'NOT_STARTED')):
                operations._append_local(target, kind, operation['operation_id'], [], state,
                    'test-only proposal', operation['created_at_utc'])
            target.commit()

    def insert_ack_fixture(self, ack=None):
        body = deepcopy(self.ack if ack is None else ack)
        with a.connect(self.config.control, write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            head = a._audit_head(control)
            body['previous_sha256'] = head['body_sha256']
            sequence = head['sequence'] + 1
            control.execute('INSERT INTO recognition_admin_audit VALUES(?,?,?)',
                             (sequence, canonical(body), digest(body)))
            control.commit()
        return sequence, body

    def test_codec_round_trip_detached_and_digest_covers_complete_audit(self):
        before = self.snapshot()
        encoded = canonical(self.ack)
        self.assertEqual(self.ack, records.parse_acknowledgement(encoded, acknowledgement_sha256=digest(self.ack)))
        self.assertEqual(digest(self.ack), records.acknowledgement_digest(self.ack))
        self.assertEqual(self.ack, self.compare())
        self.assertEqual(records.SUBJECT_FIELDS, set(self.ack['subject']))
        self.assertEqual(before, self.snapshot())
        for key in ('at_utc', 'previous_sha256'):
            changed = deepcopy(self.ack)
            changed[key] = f.at(901) if key == 'at_utc' else 'a'*64
            self.assertNotEqual(digest(self.ack), records.acknowledgement_digest(changed))

    def test_every_missing_and_extra_field_rejected(self):
        for path in ((), ('subject',), ('subject', 'local_target'), ('subject', 'creation')):
            node = self.ack
            for key in path:
                node = node[key]
            for key in list(node) + ['extra']:
                changed = deepcopy(self.ack)
                destination = changed
                for part in path:
                    destination = destination[part]
                if key == 'extra':
                    destination[key] = 'extra'
                else:
                    del destination[key]
                with self.subTest(path=path, key=key), self.assertRaises(ValueError):
                    records.acknowledgement_digest(changed)

    def test_uuid_sha_integer_and_nul_canonical_validation(self):
        cases = []
        for key in ('operation_id', 'event_id', 'preparation_id'):
            for bad in ('AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA', str(uuid4())+'\0', 'invalid', 1, True):
                cases.append((('subject', key), bad))
        for key in ('operation_sha256', 'event_sha256', 'preparation_sha256'):
            for bad in ('A'*64, 'a'*63, 'a'*64+'\0', 'a'*30+'\0'+'a'*33, True):
                cases.append((('subject', key), bad))
        for key in ('generation', 'owner_id', 'auth_epoch', 'mfa_epoch'):
            for bad in (True, False, 1.0, '1', 0, -1, 2**63):
                cases.append((('subject', 'local_target', key), bad))
        for path in (('actor',), ('subject', 'creation', 'actor_id')):
            for bad in (True, 1.0, '1', 0):
                cases.append((path, bad))
        for path, bad in cases:
            changed = deepcopy(self.ack)
            node = changed
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = bad
            with self.subTest(path=path, bad=repr(bad)), self.assertRaises(ValueError):
                records.acknowledgement_digest(changed)

    def test_json_duplicate_keys_noncanonical_float_and_timestamps_rejected(self):
        encoded = canonical(self.ack)
        candidates = [encoded+' ', json.dumps(self.ack, indent=2),
            encoded[:-1]+',"action":"'+records.ACK_ACTION+'"}',
            encoded.replace('"generation":3', '"generation":3.0'),
            encoded.replace('"generation":3', '"generation":NaN')]
        for bad_time in ('2026-1-01T00:00:00Z', f.at(900).replace('Z', '+00:00'),
                         f.at(900)+'\0', True, 900):
            changed = deepcopy(self.ack)
            changed['at_utc'] = bad_time
            candidates.append(canonical(changed))
        for value in candidates:
            with self.subTest(value=value[:70]), self.assertRaises(ValueError):
                records.parse_acknowledgement(value, acknowledgement_sha256=digest(self.ack))
        with self.assertRaisesRegex(ValueError, 'ack_digest'):
            records.parse_acknowledgement(encoded, acknowledgement_sha256='0'*64)

    def test_both_split_brain_directions(self):
        other = deepcopy(self.operation)
        other['operation_id'] = str(uuid4())
        other['creation']['request_id'] = str(uuid4())
        with runtime.authentication_transaction(self.config) as context:
            other_ack = records.build_acknowledgement(other, context=context, frozen=self.frozen,
                operation_sha256=digest(other), acknowledged_at_utc=f.at(900), previous_sha256=None)
        for operation, ack in ((self.operation, other_ack), (other, self.ack)):
            with self.subTest(operation=operation['operation_id']), self.assertRaisesRegex(ValueError, 'ack_mismatch'):
                self.compare(operation, ack)

    def test_every_scope_mismatch_even_with_unchanged_operation_digest(self):
        target = self.ack['subject']['local_target']
        for key in contract.TARGET_FIELDS - {'format'}:
            changed = deepcopy(self.ack)
            old = target[key]
            replacement = str(uuid4()) if key in ('installation_id', 'target_id') else (
                'a'*64 if type(old) is str else old+1)
            if key == 'generation':
                replacement = old-1
            changed['subject']['local_target'][key] = replacement
            if key == 'owner_id':
                changed['actor'] = changed['subject']['creation']['actor_id'] = replacement
            # This remains a structurally valid ACK with its original op digest.
            records.acknowledgement_digest(changed)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'ack_mismatch'):
                self.compare(ack=changed)

    def test_every_proposal_and_provenance_mismatch(self):
        for key in ('operation_id', 'operation_sha256', 'event_id', 'event_sha256',
                    'preparation_id', 'preparation_sha256', 'created_at_utc'):
            changed = deepcopy(self.ack)
            changed['subject'][key] = (f.at(899) if key == 'created_at_utc' else
                'b'*64 if key.endswith('sha256') else str(uuid4()))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'ack_mismatch'):
                self.compare(ack=changed)
        for key in contract.CREATION_FIELDS - {'actor_id'}:
            changed = deepcopy(self.ack)
            changed['subject']['creation'][key] = str(uuid4()) if key == 'request_id' else 'c'*64
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'ack_mismatch'):
                self.compare(ack=changed)

    def test_stale_ack_cannot_follow_changed_target_envelope(self):
        changed = deepcopy(self.operation)
        changed['creation']['request_sha256'] = 'd'*64
        with self.assertRaisesRegex(ValueError, 'ack_mismatch'):
            self.compare(changed)

    def test_durable_stale_ack_rejects_rehashed_target_change(self):
        changed = deepcopy(self.operation)
        changed['creation']['request_sha256'] = 'd'*64
        self.insert_graph_fixture(changed)
        self.insert_ack_fixture()
        with self.assertRaisesRegex(ValueError, 'ack_mismatch'):
            self.read()

    def test_future_ack_and_precreation_ack_rejected(self):
        for time in (f.at(899), f.at(901)):
            changed = deepcopy(self.ack)
            changed['at_utc'] = time
            with self.subTest(time=time), self.assertRaises(ValueError):
                self.compare(ack=changed)

    def test_real_durable_pair_reader_and_reference_are_read_only_data(self):
        self.insert_graph_fixture()
        sequence, ack = self.insert_ack_fixture()
        before = self.snapshot()
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('no key reads')), \
             patch.object(a, '_audit', side_effect=AssertionError('no audit append')):
            result = self.read()
            with runtime.authentication_transaction(self.config) as context:
                borrowed = scope.read_view(context)
                again = records.read_proposal_reference(borrowed, result['reference'],
                    session_token=self.session, primary_token=self.primary)
        self.assertEqual(result, again)
        self.assertEqual('ACKNOWLEDGED', result['status'])
        self.assertEqual(sequence, result['reference']['acknowledgement_sequence'])
        self.assertEqual(digest(ack), result['reference']['acknowledgement_sha256'])
        self.assertEqual(before, self.snapshot())
        for key in ('execution_authority', 'writer', 'capability', 'context'):
            self.assertNotIn(key, result)
        self.assertNotIn(self.primary, canonical(result))
        self.assertNotIn(self.session, canonical(result))

    def test_orphan_not_repaired_by_repeated_read_or_restart(self):
        self.insert_graph_fixture()
        before = self.snapshot()
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, 'ack_missing_or_duplicate'):
                self.read()
        self.assertEqual(before, self.snapshot())

    def test_control_ack_without_target_graph_rejected(self):
        self.insert_ack_fixture()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'record_missing'):
            self.read()
        self.assertEqual(before, self.snapshot())

    def test_duplicate_acknowledgements_rejected_even_if_identical_subject(self):
        self.insert_graph_fixture()
        self.insert_ack_fixture()
        self.insert_ack_fixture()
        with self.assertRaisesRegex(ValueError, 'ack_missing_or_duplicate'):
            self.read()

    def test_durable_split_brain_ack_other_scope_rejected(self):
        self.insert_graph_fixture()
        changed = deepcopy(self.ack)
        changed['subject']['local_target']['target_id'] = str(uuid4())
        self.insert_ack_fixture(changed)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'ack_mismatch'):
            self.read()
        self.assertEqual(before, self.snapshot())

    def test_corrupt_audit_chain_rejected(self):
        self.insert_graph_fixture()
        self.insert_ack_fixture()
        with a.connect(self.config.control, write=True) as control:
            head = a._audit_head(control)
            changed = deepcopy(self.ack)
            changed['previous_sha256'] = '0'*64
            control.execute('INSERT INTO recognition_admin_audit VALUES(?,?,?)',
                            (head['sequence']+1, canonical(changed), digest(changed)))
            control.commit()
        with self.assertRaisesRegex(ValueError, 'audit_integrity_failure'):
            self.read()

    def test_noncanonical_durable_ack_rejected_despite_matching_digest(self):
        self.insert_graph_fixture()
        body = deepcopy(self.ack)
        with a.connect(self.config.control, write=True) as control:
            head = a._audit_head(control)
            body['previous_sha256'] = head['body_sha256']
            control.execute('INSERT INTO recognition_admin_audit VALUES(?,?,?)',
                (head['sequence']+1, json.dumps(body, indent=2), digest(body)))
            control.commit()
        with self.assertRaisesRegex(ValueError, 'record_integrity'):
            self.read()

    def test_history_integer_boolean_is_not_accepted_as_sequence_one(self):
        self.insert_graph_fixture()
        self.insert_ack_fixture()
        table = 'recognition_operation_decisions'
        trigger = table + '_immutable_update'
        with a.connect(self.config.target, write=True) as target:
            row = target.execute(f'SELECT body_json FROM {table} WHERE operation_id=?',
                                  (self.operation['operation_id'],)).fetchone()
            body = json.loads(row[0])
            body['sequence'] = True
            target.execute('DROP TRIGGER ' + trigger)
            target.execute(f'UPDATE {table} SET body_json=?,body_sha256=? WHERE operation_id=?',
                (canonical(body), digest(body), self.operation['operation_id']))
            target.execute(operation_schema.definitions()[trigger])
            target.commit()
        with self.assertRaisesRegex(ValueError, 'runtime_contract_integer'):
            self.read()

    def test_invalidated_event_is_not_an_initial_proposal(self):
        self.insert_graph_fixture()
        self.insert_ack_fixture()
        with a.connect(self.config.target, write=True) as target:
            old = events.get_event(target, self.operation['event_id'])
            item = dict(event_id=self.operation['event_id'], sequence=2, state='INVALID',
                reason='test-only invalidation', recorded_at_utc=f.at(900), previous_sha256=digest(old['history'][0]))
            events._insert(target, 'recognition_event_history', 'event_id,sequence',
                           (self.operation['event_id'], 2), item)
            target.commit()
        with self.assertRaisesRegex(ValueError, 'event_not_initial'):
            self.read()

    def test_receipt_record_does_not_turn_ack_into_execution(self):
        self.insert_graph_fixture()
        self.insert_ack_fixture()
        with a.connect(self.config.target, write=True) as target:
            events._insert(target, 'recognition_operation_receipts', 'operation_id',
                           (self.operation['operation_id'],), {'test_only': 'unexpected receipt'})
            target.commit()
        with self.assertRaisesRegex(ValueError, 'unexpected_downstream_record'):
            self.read()

    def test_reference_cannot_substitute_sequence_or_digest(self):
        self.insert_graph_fixture()
        self.insert_ack_fixture()
        result = self.read()
        for key in records.REFERENCE_FIELDS - {'format'}:
            changed = deepcopy(result['reference'])
            changed[key] = (changed[key]+1 if key == 'acknowledgement_sequence' else
                str(uuid4()) if key == 'operation_id' else '0'*64)
            with self.subTest(key=key), self.assertRaises(ValueError):
                with runtime.authentication_transaction(self.config) as context:
                    records.read_proposal_reference(context, changed,
                        session_token=self.session, primary_token=self.primary)

    def test_detached_context_and_missing_authentication_rejected(self):
        with self.assertRaises(ValueError):
            records.read_acknowledged_proposal({}, self.operation['operation_id'],
                session_token=self.session, primary_token=self.primary)
        with self.assertRaises(ValueError):
            with runtime.authentication_transaction(self.config) as context:
                records.read_acknowledged_proposal(context, self.operation['operation_id'],
                    session_token='x'*32, primary_token=self.primary)

    def test_legacy_operation_is_not_wrapped_or_migrated(self):
        legacy_id = self.fixture.fixture.f.operation['envelope']['operation_id']
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'v2_required'):
            self.read(legacy_id)
        self.assertEqual(before, self.snapshot())

    def test_ack_pair_does_not_open_any_downstream_gate(self):
        self.insert_graph_fixture()
        self.insert_ack_fixture()
        result = self.read()
        before = self.snapshot()
        for call in (
            lambda: production_operations.load_context(self.config, self.operation['operation_id']),
            lambda: production_operations.load_recovery_context(self.config, self.operation['operation_id']),
            lambda: production_operations.discover_pending(self.config),
            lambda: approvals.create_approval(self.config, self.session, 'x'*32, 'y'*32,
                operation_id=self.operation['operation_id'], reason='must not approve', now=f.at(900)),
            lambda: writer_boundary.acquire(result, self.config.target, self.frozen['preparation']['manifest'])):
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()
        execution = local_execution.execute_approved_operation(result, self.session, str(uuid4()), now=f.at(900))
        self.assertEqual('BLOCKED', execution.admission)
        self.assertFalse(local_readiness.assess(self.config, now=f.at(900))['activation_ready'])
        self.assertEqual(before, self.snapshot())

    def test_legacy_control_creation_collision_is_not_reinterpreted(self):
        self.insert_graph_fixture()
        with a.connect(self.config.control, write=True) as control:
            a._audit(control, 'production_operation_created', 1, f.at(900),
                dict(operation_id=str(uuid4()), operation_sha256='a'*64,
                     request_id=self.operation['creation']['request_id']))
            control.commit()
        self.insert_ack_fixture()
        with self.assertRaisesRegex(ValueError, 'legacy_creation_conflict'):
            self.read()

    def test_creation_references_are_not_current_authentication(self):
        self.insert_graph_fixture()
        self.insert_ack_fixture()
        fixture = self.fixture.fixture
        fixture.sql('UPDATE recognition_admin_primary SET revoked=1 WHERE token_hash=?',
                    (a.token_hash(self.primary),))
        with self.assertRaises(ValueError):
            self.read()
        fixture.clock.return_value = f.at(930)
        self.primary = fixture.primary()
        self.session = fixture.session(self.primary)
        result = self.read()
        self.assertEqual(self.operation['creation'], result['operation']['creation'])
        self.assertNotEqual(a.token_hash(self.primary), result['operation']['creation']['primary_sha256'])


if __name__ == '__main__':
    unittest.main()

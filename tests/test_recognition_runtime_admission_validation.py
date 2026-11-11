"""Reservation-bound extraction: real enrolled/authenticated/approved lifecycle."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from dataclasses import replace
import json
import os
import pickle
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, authorization, approvals
from src.review.recognition import runtime_admission_validation as shared
from src.review.recognition import runtime_claim_validation as claim
from src.review.recognition import runtime_proposal_transaction as proposal
from src.review.recognition import runtime_execution_admission as admission
from src.review.recognition import runtime_scope_validation as scope, runtime_validation as runtime
from src.review.recognition import runtime_execution_claim_schema as schema
from src.review.recognition import execution, local_execution, local_readiness, writer_boundary, production_operations
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_execution_admission as lifecycle
from tests import test_recognition_administration as f


class SharedAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f = lifecycle.RuntimeExecutionAdmissionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.config = self.f.config
        self.snapshot = self.f.assess()
        self.clock = self.f.clock

    def validate(self, view, snapshot=None, session=None):
        return shared.validate(view, self.snapshot if snapshot is None else snapshot,
            self.f.session if session is None else session, primary_token=self.f.primary)

    def owners(self):
        return ((proposal.proposal_transaction, shared.proposal_read_view, proposal._state),
                (claim.validation_transaction, shared.claim_read_view, claim._state))

    def dump(self):
        return self.f.snapshot()

    def test_both_owners_same_complete_result_delete_wal_no_writes_no_authority(self):
        with patch.object(a, 'target_identity', side_effect=authorization.target_identity):
            schema.migrate(self.config, expected_generation=3, operator='fixture', reason='disposable migration')
        for mode in ('DELETE', 'WAL'):
            for path in (self.config.control, self.config.target):
                with closing(sqlite3.connect(path)) as conn:
                    conn.execute('PRAGMA journal_mode='+mode)
            before = self.dump()
            leases = (dict(writer_boundary._leases), dict(writer_boundary._local_leases), dict(production_operations._contexts))
            for manager, factory, get_state in self.owners():
                with self.subTest(mode=mode, owner=manager.__name__):
                    with patch('pathlib.Path.read_bytes', side_effect=AssertionError('no key reads')):
                        with manager(self.config) as context:
                            state = get_state(context)
                            changes = (state.control.total_changes, state.target.total_changes)
                            result = self.validate(factory(context))
                            self.assertEqual(self.snapshot.canonical_json, result.canonical_json)
                            self.assertEqual(self.snapshot.sha256, result.sha256)
                            self.assertEqual(changes, (state.control.total_changes, state.target.total_changes))
                            self.assertEqual(1, state.target.execute('PRAGMA query_only').fetchone()[0])
                            self.assertFalse(writer_boundary.verify_local(result, self.config.target, {}))
                            with self.assertRaises(ValueError): execution._context(result)
                            with self.assertRaises(ValueError): production_operations.context_data(result)
                    with self.assertRaises(ValueError): result.snapshot
                    self.assertEqual(before, self.dump())
            self.assertEqual(leases, (dict(writer_boundary._leases), dict(writer_boundary._local_leases), dict(production_operations._contexts)))
            with a.connect(self.config.control) as control:
                for table in (schema.CLAIMS, schema.HISTORY):
                    self.assertEqual(0, control.execute('SELECT count(*) FROM '+table).fetchone()[0])
                body = json.loads(control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
                self.assertEqual('NOT_ACTIVATED', body['production_state'])
            self.assertFalse(local_readiness.assess(self.config, now=self.clock.return_value)['activation_ready'])
            with self.assertRaisesRegex(a.AdminError, 'runtime_profile_contract_not_enabled'):
                a.get_installation_control(self.config)
            self.assertEqual('BLOCKED', local_execution.execute_approved_operation(self.snapshot, self.f.session,
                self.f.approval['approval']['approval_id'], now=self.clock.return_value).admission)

    def test_exact_owner_types_no_sql_or_handles_no_detached_input(self):
        for manager, factory, _ in self.owners():
            with manager(self.config) as context:
                view = factory(context)
                other = shared.claim_read_view if factory is shared.proposal_read_view else shared.proposal_read_view
                with self.assertRaises(ValueError): other(context)
                with self.assertRaises(ValueError): scope.read_view(context)
                if factory is shared.claim_read_view:
                    with self.assertRaises(ValueError): proposal.read_view(context)
                else:
                    with self.assertRaises(ValueError): claim._state(context)
                result = self.validate(view)
                for obj in (view, result):
                    for name in ('execute','cursor','control','target','commit','rollback','close','writer','acquire'):
                        self.assertFalse(hasattr(obj, name))
                    with self.assertRaises(TypeError): pickle.dumps(obj)
                with self.assertRaises(TypeError): result.snapshot['runtime_scope']['generation'] = 99
                for fake in (dict(self.snapshot.snapshot), self.snapshot.canonical_json,
                             object.__new__(admission.ExecutionAdmission)):
                    with self.assertRaises(ValueError): self.validate(view, snapshot=fake)
                with self.assertRaises(ValueError): self.validate(object.__new__(shared.AdmissionReadView))
            with self.assertRaises(ValueError): self.validate(view)
            for access in (lambda: result.snapshot, lambda: result.sha256, lambda: result.canonical_json):
                with self.assertRaises(ValueError): access()
        with self.assertRaises(TypeError): shared.AdmissionReadView()
        with self.assertRaises(TypeError): shared.BoundAdmission()

    def test_complete_comparison_each_security_field_after_real_validation(self):
        paths = [('runtime_scope', key) for key in ('runtime_profile_sha256','generation','installation_id',
            'target_id','owner_id','auth_epoch','mfa_epoch','binding_sha256')]
        paths += [('proposal','operation_id'), ('proposal','writer_manifest_sha256'),
            ('reference','operation_sha256'), ('reference','acknowledgement_sha256'),
            ('acknowledgement','previous_sha256'), ('approval','approval_id'),
            ('approval_sha256',), ('approval_history_sha256',), ('dependency_snapshot','format'),
            ('target_snapshot','target','schema_sha256'),
            ('authentication','primary_sha256'), ('authentication','session_sha256'),
            ('emergency_stop_snapshot','sequence')]
        for prefix in (('target_snapshot','target','observation'), ('target_snapshot','control_identity')):
            paths += [prefix+(key,) for key in ('hostname','database','device','inode')]
        real = shared._collect
        for manager, factory, _ in self.owners():
            with manager(self.config) as context:
                view = factory(context)
                for path in paths:
                    def changed(*args, **kwargs):
                        # Fault only AFTER the real reader completes all durable
                        # validation. Independently prove complete T1/T2 comparison.
                        body = deepcopy(real(*args, **kwargs))
                        part = body
                        for key in path[:-1]: part = part[key]
                        value = part[path[-1]]
                        part[path[-1]] = value+1 if type(value) is int else ('changed' if value is None else value+'-changed')
                        return body
                    with self.subTest(owner=manager.__name__, path=path):
                        with patch.object(shared, '_collect', side_effect=changed), self.assertRaisesRegex(ValueError, 'runtime_admission_snapshot_stale'):
                            self.validate(view)
                self.validate(view)

    def test_pid_thread_and_lifetime(self):
        for manager, factory, _ in self.owners():
            with manager(self.config) as context:
                view = factory(context)
                result = self.validate(view)
                with patch.object(os, 'getpid', return_value=-1), self.assertRaises(ValueError): result.sha256
                with ThreadPoolExecutor(max_workers=1) as pool:
                    with self.assertRaises(ValueError): pool.submit(lambda: self.validate(view)).result(timeout=5)
                    # Independently exercise the borrowed view's owner check;
                    # validate() also fences the original 4d-0 snapshot thread.
                    with self.assertRaises(ValueError): pool.submit(lambda: result.sha256).result(timeout=5)
                self.assertEqual(self.snapshot.sha256, self.validate(view).sha256)
            with self.assertRaises(ValueError): result.sha256

    def test_reservation_replacement_detected_even_when_in_transaction_again(self):
        for mode in ('DELETE','WAL'):
            for path in (self.config.control,self.config.target):
                with closing(sqlite3.connect(path)) as conn: conn.execute('PRAGMA journal_mode='+mode)
            before = self.dump()
            with proposal.proposal_transaction(self.config) as context:
                view = shared.proposal_read_view(context)
                result = self.validate(view)
                # Real fixed manager helper releases and reacquires. Existing
                # proposal semantics stay valid, borrowed admission must not.
                state = proposal._state(context)
                # The existing persistence helper requires its owner's normal
                # query-only-off phase before committing/reacquiring.
                proposal._target_query_only(state, False)
                proposal._target_commit_and_reserve(state)
                self.assertTrue(proposal._state(context).target.in_transaction)
                with self.assertRaisesRegex(ValueError, 'runtime_admission_reservation_invalid'): self.validate(view)
                with self.assertRaises(ValueError): result.snapshot
                self.validate(shared.proposal_read_view(context))
            self.assertEqual(before, self.dump())

    def test_release_replacement_query_only_and_lifecycle_poison(self):
        for manager, factory, get_state in self.owners():
            for mode in ('DELETE','WAL'):
                for path in (self.config.control,self.config.target):
                    with closing(sqlite3.connect(path)) as conn: conn.execute('PRAGMA journal_mode='+mode)
                for attack in ('ROLLBACK','COMMIT','BEGIN IMMEDIATE','PRAGMA query_only=OFF',
                               'CREATE TABLE prohibited(x)','DELETE FROM recognition_frozen_events'):
                    before = self.dump()
                    with self.subTest(owner=manager.__name__, mode=mode, attack=attack), self.assertRaises(ValueError):
                        with manager(self.config) as context:
                            view = factory(context)
                            state = get_state(context)
                            # Trusted test fault injection at the internal raw
                            # connection; its real authorizer must deny/poison.
                            with self.assertRaises(sqlite3.DatabaseError): state.target.execute(attack)
                            with self.assertRaises(ValueError): self.validate(view)
                    self.assertEqual(before, self.dump())

    def test_connection_replacement_and_manager_release_invalidate_view(self):
        for manager, factory, get_state in self.owners():
            for which in ('control','target'):
                with self.assertRaises(ValueError):
                    with manager(self.config) as context:
                        view = factory(context)
                        state = get_state(context)
                        original = getattr(state,which)
                        with a.connect(getattr(self.config,which), write=True) as replacement:
                            replacement.execute('BEGIN' if which == 'target' else 'BEGIN')
                            setattr(state,which,replacement)
                            try:
                                with self.assertRaises(ValueError): self.validate(view)
                            finally:
                                setattr(state,which,original)
                        state.poisoned = True
            with self.assertRaises(ValueError):
                with manager(self.config) as context:
                    view = factory(context)
                    state = get_state(context)
                    state.lifecycle = True
                    state.target.rollback()  # Simulate an internal owner fault.
                    state.lifecycle = False
                    with self.assertRaises(ValueError): self.validate(view)

    def test_control_reservation_and_query_protection_replacement_are_not_reusable(self):
        for manager, factory, get_state in self.owners():
            for change in ('control_transaction','target_transaction','query_only'):
                with manager(self.config) as context:
                    view = factory(context)
                    state = get_state(context)
                    state.lifecycle = True
                    try:
                        if change == 'control_transaction':
                            state.control.rollback()
                            state.control.execute('BEGIN IMMEDIATE')
                        elif change == 'target_transaction':
                            state.target.rollback()
                            # A deferred replacement passes in_transaction but
                            # has lost the original writer reservation.
                            state.target.execute('BEGIN')
                        else:
                            state.target.execute('PRAGMA query_only=OFF')
                            state.target.execute('PRAGMA query_only=ON')
                    finally:
                        state.lifecycle = False
                    self.assertTrue(state.control.in_transaction and state.target.in_transaction)
                    with self.assertRaisesRegex(ValueError,'runtime_admission_reservation_invalid'): self.validate(view)

    def test_expiry_on_live_result_and_final_commit_preserves_deadlines(self):
        for manager, factory, get_state in self.owners():
            with manager(self.config) as context:
                result = self.validate(factory(context))
                state = get_state(context)
                self.assertTrue(state.auth_expiries)
                before = list(state.auth_expiries)
                now = self.clock.return_value
                self.clock.return_value = f.at(40000)
                try:
                    with self.assertRaises(ValueError): result.snapshot
                finally:
                    self.clock.return_value = now
                self.assertEqual(before, state.auth_expiries)
            with self.assertRaises(ValueError):
                with manager(self.config) as context:
                    self.validate(factory(context))
                    self.clock.return_value = f.at(40000)
            self.clock.return_value = now

    def test_actual_revoked_session_rejects(self):
        self._changed_authentication('recognition_admin_sessions','revoked=1')

    def test_actual_revoked_primary_rejects(self):
        self._changed_authentication('recognition_admin_primary','revoked=1')

    def test_invalid_session_rejects_with_existing_denial_semantics(self):
        for manager, factory, _ in self.owners():
            with self.assertRaises(ValueError):
                with manager(self.config) as context: self.validate(factory(context),session='x'*32)

    def test_clock_rollback_invalidates_live_result_without_refresh(self):
        original = self.clock.return_value
        for manager, factory, _ in self.owners():
            with manager(self.config) as context:
                self.clock.return_value = f.at(960)
                result = self.validate(factory(context))
                self.clock.return_value = original
                with self.assertRaisesRegex(ValueError,'runtime_admission_clock_rollback'): result.sha256
                self.clock.return_value = f.at(960)
            self.clock.return_value = original

    def test_actual_changed_mfa_epoch_rejects_with_previously_valid_proofs(self):
        self._changed_authentication('recognition_admin_mfa','epoch=epoch+1')

    def _changed_authentication(self, table, statement):
        with a.connect(self.config.control,write=True) as control:
            control.execute('UPDATE '+table+' SET '+statement)
            control.commit()
        for manager, factory, _ in self.owners():
            with self.subTest(table=table, owner=manager.__name__), self.assertRaises(ValueError):
                with manager(self.config) as context: self.validate(factory(context))

    def test_real_approval_invalidation_rejects_both_paths(self):
        with a.connect(self.config.control,write=True) as control:
            control.execute('BEGIN IMMEDIATE')
            approvals._invalidate_all(control,'owner',self.clock.return_value,'explicit invalidation')
            control.commit()
        for manager, factory, _ in self.owners():
            with self.assertRaises(ValueError):
                with manager(self.config) as context: self.validate(factory(context))
        with self.assertRaises(ValueError): self.f.assess()

    def test_actual_emergency_stop_rejects_both_paths(self):
        body = dict(active=True,sequence=1,previous_sha256=None)
        with a.connect(self.config.control,write=True) as control:
            control.execute('INSERT INTO recognition_execution_stops VALUES(?,?,?)',(1,canonical(body),digest(body)))
            control.commit()
        for manager, factory, _ in self.owners():
            with self.assertRaisesRegex(ValueError,'emergency_stop'):
                with manager(self.config) as context: self.validate(factory(context))
        with self.assertRaisesRegex(ValueError,'emergency_stop'): self.f.assess()

    def test_actual_dependency_change_rejects_both_paths(self):
        with a.connect(self.config.target,write=True) as target:
            target.execute("UPDATE stop_review_assignments SET status='assigned' WHERE id=(SELECT MIN(id) FROM stop_review_assignments)")
            target.commit()
        for manager, factory, _ in self.owners():
            with self.assertRaises(ValueError):
                with manager(self.config) as context: self.validate(factory(context))
        with self.assertRaises(ValueError): self.f.assess()

    def test_actual_physical_observer_mismatch_and_schema_reject(self):
        real = a.target_identity
        for field in ('hostname','database','device','inode'):
            def changed(subject):
                result = real(subject)
                value = getattr(result,field)
                return replace(result,**{field:value+1 if type(value) is int else value+'-changed'})
            for manager, factory, _ in self.owners():
                with self.subTest(field=field,owner=manager.__name__):
                    with patch.object(a,'target_identity',side_effect=changed), self.assertRaises(ValueError):
                        with manager(self.config) as context: self.validate(factory(context))
        with a.connect(self.config.target,write=True) as target:
            target.execute('CREATE TABLE changed_schema(x)'); target.commit()
        for manager, factory, _ in self.owners():
            with self.assertRaises(ValueError):
                with manager(self.config) as context: self.validate(factory(context))

    def test_both_reservations_retained_through_control_commit(self):
        finish = proposal._finish
        def checked(state):
            for path in (self.config.control,self.config.target):
                with closing(sqlite3.connect(path,timeout=0)) as conn:
                    with self.assertRaises(sqlite3.OperationalError): conn.execute('BEGIN IMMEDIATE')
            finish(state)
            # Control is committed; target is STILL reserved until owner exit.
            self.assertFalse(state.control.in_transaction)
            self.assertTrue(state.target.in_transaction)
            with closing(sqlite3.connect(self.config.target,timeout=0)) as conn:
                with self.assertRaises(sqlite3.OperationalError): conn.execute('BEGIN IMMEDIATE')
        for manager, factory, _ in self.owners():
            with patch.object(proposal,'_finish',side_effect=checked):
                with manager(self.config) as context: self.validate(factory(context))
            for path in (self.config.control,self.config.target):
                with closing(sqlite3.connect(path,timeout=0)) as conn:
                    conn.execute('BEGIN IMMEDIATE'); conn.rollback()

    def test_failed_collection_rolls_back_and_never_publishes_result(self):
        before = self.dump()
        from src.review.recognition import permanent
        for manager, factory, _ in self.owners():
            count = len(shared._results)
            with patch.object(permanent,'_prepare',side_effect=sqlite3.OperationalError('read failed')):
                with self.assertRaises(sqlite3.OperationalError):
                    with manager(self.config) as context: self.validate(factory(context))
            self.assertEqual(count,len(shared._results))
            self.assertEqual(before,self.dump())

    def test_claim_registration_has_no_control_insertion_authority(self):
        with patch.object(a, 'target_identity', side_effect=authorization.target_identity):
            schema.migrate(self.config, expected_generation=3, operator='fixture', reason='disposable migration')
        before = self.dump()
        for table in (schema.CLAIMS, schema.HISTORY, 'recognition_approvals', 'recognition_admin_primary',
                      'recognition_runtime_auth_bindings', 'recognition_admin_audit'):
            with self.subTest(table=table), self.assertRaises(ValueError):
                with claim.validation_transaction(self.config) as context:
                    view = shared.claim_read_view(context)
                    self.validate(view)
                    with self.assertRaises(sqlite3.DatabaseError):
                        claim._state(context).control.execute('INSERT INTO '+table+' DEFAULT VALUES')
                    with self.assertRaises(ValueError): self.validate(view)
            self.assertEqual(before,self.dump())

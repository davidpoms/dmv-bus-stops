"""Direct writer authorization tests; only synthetic temporary databases."""

from dataclasses import asdict, replace
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import RecognitionGate, permanent, live_first_looks as live
from src.review.recognition import authorization as auth, permanent_schema, live_first_look_schema
from src.review.recognition.rules import digest
from src.review.recognition.schema import connection
from tests import test_recognition_permanent as permanent_fixture
from tests import test_live_first_looks as live_fixture
from tests.recognition_authorization_fixture import FixtureAuthority, migrate_private, sealing_binding


ISSUE = RecognitionGate(issuance=True)
CAPTURE = RecognitionGate(capture=True)


def mutations(approval):
    return [None, {}, replace(approval, environment='other'),
            replace(approval, target=replace(approval.target, inode=approval.target.inode + 1)),
            replace(approval, family='explorer'), replace(approval, action='enqueue'),
            replace(approval, permission='capture'), replace(approval, operation_sha256='0' * 64),
            replace(approval, policy_sha256='0' * 64), replace(approval, population_sha256='0' * 64),
            replace(approval, reference='wrong-reference'), replace(approval, policy_sha256='not-a-hash'),
            replace(approval, expires_at_utc='2000-01-01T00:00:00Z')]


class PermanentAuthorizationTests(unittest.TestCase):
    sql = permanent_fixture.PermanentFamilyTests.sql
    review = permanent_fixture.PermanentFamilyTests.review
    first = permanent_fixture.PermanentFamilyTests.first
    geo = permanent_fixture.PermanentFamilyTests.geo
    scope = permanent_fixture.PermanentFamilyTests.scope
    envelope = permanent_fixture.PermanentFamilyTests.envelope

    def setUp(self):
        permanent_fixture.PermanentFamilyTests.setUp(self)
        for n in range(1, 6):
            self.review(n)
        migrate_private(self.path, apply=True)
        self.authority = FixtureAuthority()

    def issue(self, manifest, authorization=None, authority=None):
        return permanent.finalize(self.path, manifest, manifest_sha256=digest(manifest),
            authorization_reference=manifest['authorization_reference'], gate=ISSUE,
            authorization=authorization, authority=authority)

    def test_both_families_reject_missing_malformed_or_mismatched_approval(self):
        for manifest in (self.first(), self.geo()):
            approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
            before = self.path.read_bytes()
            for invalid in mutations(approved):
                # Even an authority that recognizes the altered artifact cannot
                # override the writer's independently recomputed binding.
                if isinstance(invalid, auth.Authorization):
                    self.authority.approved.add(invalid)
                with self.subTest(family=manifest['family'], invalid=invalid), self.assertRaises(auth.AuthorizationError):
                    self.issue(manifest, invalid, self.authority.authority)
                self.assertEqual(before, self.path.read_bytes())

    def test_missing_custom_and_accepting_callbacks_are_not_authorities(self):
        manifest = self.first()
        approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
        before = self.path.read_bytes()
        class Accepting:
            def __call__(self, approval):
                return True
        for impostor in (None, lambda _: True, Accepting(), object()):
            with self.subTest(authority=impostor), self.assertRaises(auth.AuthorizationError):
                self.issue(manifest, approved, impostor)
        self.authority.approved.remove(approved)
        with self.assertRaises(auth.AuthorizationError):
            self.issue(manifest, approved, self.authority.authority)
        self.assertEqual(before, self.path.read_bytes())

    def test_revocation_during_writer_rolls_back_all_inserts(self):
        manifest = self.geo()
        approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
        original = permanent._verify_operation_records
        def revoke(conn, operation):
            original(conn, operation)
            self.authority.approved.remove(approved)
        with patch.object(permanent, '_verify_operation_records', side_effect=revoke), \
             self.assertRaises(auth.AuthorizationError):
            self.issue(manifest, approved, self.authority.authority)
        self.assertEqual([(0,)], self.sql('SELECT COUNT(*) FROM recognition_private_operations'))
        self.assertEqual([(0,)], self.sql('SELECT COUNT(*) FROM recognition_geography_awards'))

    def test_direct_insert_helpers_are_not_callable_apis(self):
        self.assertFalse(hasattr(permanent, '_insert_operation'))
        self.assertFalse(hasattr(permanent, '_insert_first_look_claim'))

    def test_geography_approved_snapshot_and_explorer_preserved(self):
        manifest = self.geo()
        approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
        before = {name: self.sql('SELECT * FROM ' + name) for name in
                  ('recognition_jobs', 'recognition_awards', 'recognition_award_witnesses')}
        self.assertTrue(self.issue(manifest, approved, self.authority.authority)['issued'])
        self.assertTrue(self.issue(manifest, approved, self.authority.authority)['idempotent'])
        self.assertEqual(before, {name: self.sql('SELECT * FROM ' + name) for name in before})
        self.assertEqual([(2,)], self.sql('SELECT COUNT(*) FROM recognition_geography_awards'))

    def test_disposable_label_is_not_approval_and_production_label_cannot_reuse_it(self):
        manifest = self.first()
        approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
        with self.assertRaises(auth.AuthorizationError):
            self.issue(manifest, approved)
        with self.assertRaises(auth.AuthorizationError):
            self.issue(manifest, replace(approved, environment='production'), self.authority.authority)

    def test_file_migrations_and_direct_install_require_exact_approval(self):
        for module, family, definitions in (
                (permanent_schema, 'private_recognition', permanent_schema.definitions()),
                (live_first_look_schema, 'first_look', live_first_look_schema.OBJECTS)):
            before = self.path.read_bytes()
            with self.assertRaises(auth.AuthorizationError):
                module.migrate(self.path, apply=True)
            with connection(self.path, write=True) as conn:
                conn.execute('BEGIN IMMEDIATE')
                with self.assertRaises(auth.AuthorizationError):
                    module.install(conn)
            self.assertEqual(before, self.path.read_bytes())
            self.assertFalse(module.migrate(self.path)['applied'])
            self.assertEqual(before, self.path.read_bytes())
            approved = self.authority.approve(self.path, **auth.migration_binding(family, definitions))
            with self.assertRaises(auth.AuthorizationError):
                module.migrate(self.path, apply=True, authorization=replace(approved, operation_sha256='0'*64),
                               authority=self.authority.authority)
            module.migrate(self.path, apply=True, authorization=approved, authority=self.authority.authority)

    def test_memory_rehearsal_cannot_hide_attached_file(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.execute('ATTACH DATABASE ? AS external', (str(self.path),))
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('BEGIN')
        with self.assertRaisesRegex(auth.AuthorizationError, 'attached_database'):
            permanent_schema.install(conn)

    def test_production_provisioning_and_forged_handles_fail_closed(self):
        from src.review.recognition.authority import Authority, provision_production_authority
        manifest = self.first()
        approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
        with self.assertRaises(auth.AuthorizationError):
            provision_production_authority()
        with self.assertRaises(TypeError):
            Authority()
        with self.assertRaises(auth.AuthorizationError):
            self.issue(manifest, approved, object.__new__(Authority))
        with self.assertRaises(TypeError):
            permanent.finalize(self.path, manifest, manifest_sha256=digest(manifest),
                authorization_reference=manifest['authorization_reference'], gate=ISSUE,
                authorization=approved, authorization_verifier=lambda _: True)

    def test_test_authority_cannot_enroll_existing_target_or_relabel_environment(self):
        from tests.recognition_authorization_fixture import DisposableWorkspace
        workspace = DisposableWorkspace()
        self.addCleanup(workspace.cleanup)
        manifest = self.first()
        # This existing database is outside the new authority's allocated root.
        forged = auth.Authorization(target=auth.target_identity(self.path), environment='disposable',
                                    **auth.manifest_binding(manifest))
        workspace.approved.add(forged)
        for environment in ('production', 'disposable'):
            with self.subTest(environment=environment), self.assertRaises(auth.AuthorizationError):
                self.issue(manifest, replace(forged, environment=environment), workspace.authority)
        # Mutable provisioning-wrapper attributes cannot change the enrolled root.
        workspace.name = str(self.path.parent)
        with self.assertRaises(auth.AuthorizationError):
            self.issue(manifest, forged, workspace.authority)
        approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
        relabeled = replace(approved, environment='production')
        self.authority.approved.add(relabeled)
        with self.assertRaises(auth.AuthorizationError):
            self.issue(manifest, relabeled, self.authority.authority)

    def test_manifest_and_candidate_mutation_during_verification_is_frozen(self):
        from src.review.recognition import authority as provision
        manifest = self.first()
        original_hash = digest(manifest)
        approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
        original_check = provision.check_authority
        def mutate(handle, authorization):
            manifest['authorization_reference'] = 'unapproved-reference'
            manifest['candidates'][0]['reviewer_id'] = 999
            original_check(handle, authorization)
        with patch.object(provision, 'check_authority', side_effect=mutate):
            result = self.issue(manifest, approved, self.authority.authority)
        self.assertEqual(original_hash, result['operation_id'])
        self.assertEqual([('synthetic-authorization',)], self.sql(
            'SELECT authorization_reference FROM recognition_private_operations'))
        self.assertNotIn((999,), self.sql('SELECT reviewer_id FROM recognition_first_look_claims'))

    def test_discrepancy_mutation_during_verification_is_frozen(self):
        from src.review.recognition import authority as provision
        from src.review.recognition.rules import canonical
        manifest = self.first()
        approved = self.authority.approve(self.path, **auth.manifest_binding(manifest))
        self.issue(manifest, approved, self.authority.authority)
        evidence = {'reason': 'reviewed', 'nested': {'value': 'approved'}}
        body = dict(physical_stop_id=1, evidence=evidence, review_reference='synthetic-review',
                    reviewed_at_utc='2026-10-04T00:00:00Z')
        frozen = canonical(body)
        approved = self.authority.approve(self.path, family='first_look', permission='issuance',
            action='append_discrepancy', operation_sha256=digest(body),
            policy_sha256=digest(permanent.DEFINITIONS['first_look']), population_sha256=None,
            reference=body['review_reference'])
        original_check = provision.check_authority
        def mutate(handle, authorization):
            evidence['nested']['value'] = 'unapproved'
            original_check(handle, authorization)
        with patch.object(provision, 'check_authority', side_effect=mutate):
            permanent.append_discrepancy(self.path, **body, gate=ISSUE,
                authorization=approved, authority=self.authority.authority)
        self.assertEqual([(frozen, approved.operation_sha256)], self.sql(
            'SELECT evidence_json,evidence_sha256 FROM recognition_first_look_discrepancies'))


class LiveAuthorizationTests(unittest.TestCase):
    sql = live_fixture.LiveFirstLookTests.sql
    review = live_fixture.LiveFirstLookTests.review
    seal_baseline = live_fixture.LiveFirstLookTests.seal_baseline
    add_live = live_fixture.LiveFirstLookTests.add_live
    guard = live_fixture.LiveFirstLookTests.guard
    pending = live_fixture.LiveFirstLookTests.pending

    def setUp(self):
        live_fixture.LiveFirstLookTests.setUp(self)
        self.seal_baseline()
        self.add_live()
        self.authority = FixtureAuthority()

    def sealing_approval(self, conn):
        config = asdict(live_fixture.CONFIG)
        fact = live.qualify(conn, 2)
        decision = self.guard(conn, {'configuration': config})
        self.delivery = self.authority.approve(conn, **live.delivery_binding(conn, 2))
        return self.authority.approve(conn, **sealing_binding(conn, config, fact, decision))

    def test_capture_requires_approval_and_rejects_issuance_only_approval(self):
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            issuance = self.sealing_approval(conn)
        self.review(3, captured=False, timestamp='2026-10-01T13:00:00Z')
        before = self.path.read_bytes()
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            for invalid in (None, issuance):
                with self.assertRaises(auth.AuthorizationError):
                    live.enqueue(conn, 3, configuration=live_fixture.CONFIG, gate=CAPTURE,
                                 authorization=invalid, authority=self.authority.authority)
        self.assertEqual(before, self.path.read_bytes())

    def test_direct_sealer_cannot_use_finality_as_authorization(self):
        before = self.pending()
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with self.assertRaises(auth.AuthorizationError):
                live.seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard)
            conn.commit()
        self.assertEqual(before, self.pending())

    def test_missing_approval_cannot_even_quarantine_bad_evidence(self):
        self.sql("UPDATE stop_observations SET reviewer_id=2 WHERE assignment_id=2")
        before = self.pending()
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with self.assertRaises(auth.AuthorizationError):
                live.seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard)
            conn.commit()
        self.assertEqual(before, self.pending())

    def test_live_binding_mismatches_and_capture_permission_cannot_seal(self):
        before = self.pending()
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            approved = self.sealing_approval(conn)
            for invalid in mutations(approved):
                if isinstance(invalid, auth.Authorization):
                    self.authority.approved.add(invalid)
                with self.subTest(invalid=invalid), self.assertRaises(auth.AuthorizationError):
                    live.seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard,
                                      authorization=invalid, authority=self.authority.authority, delivery_authorization=self.delivery)
            conn.commit()
        self.assertEqual(before, self.pending())

    def test_approval_does_not_replace_finality_and_caller_rollback_wins(self):
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            approved = self.sealing_approval(conn)
            kwargs = dict(gate=ISSUE, authorization=approved, authority=self.authority.authority, delivery_authorization=self.delivery)
            self.assertEqual('pending', live.seal_pending(conn, 2, **kwargs)['state'])
            kwargs['delivery_authorization'] = self.authority.approve(conn, **live.delivery_binding(conn, 2))
            self.assertEqual('done', live.seal_pending(conn, 2, finality_guard=self.guard, **kwargs)['state'])
            self.assertTrue(conn.in_transaction)
        self.assertEqual(('pending', 0, None, None), self.pending())
        self.assertEqual([(1,)], self.sql('SELECT COUNT(*) FROM recognition_first_look_claims'))

    def test_revoked_approval_preserves_pending(self):
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            approved = self.sealing_approval(conn)
            self.authority.approved.clear()
            with self.assertRaises(auth.AuthorizationError):
                live.seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard,
                                  authorization=approved, authority=self.authority.authority, delivery_authorization=self.delivery)
            conn.commit()
        self.assertEqual(('pending', 0, None, None), self.pending())

    def test_verifier_quarantine_does_not_authorize_delivery_mutation(self):
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            approved = self.sealing_approval(conn)
            def unavailable(candidate):
                raise permanent.Quarantined('synthetic-approval-store-unavailable')
            with self.assertRaisesRegex(auth.AuthorizationError, 'provisioned_authority_required'):
                live.seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard,
                                  authorization=approved, authority=unavailable, delivery_authorization=self.delivery)
            conn.commit()
        self.assertEqual(('pending', 0, None, None), self.pending())

    def test_same_policy_cannot_reuse_approval_for_changed_population(self):
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            approved = self.sealing_approval(conn)
        self.add_live(3, stop=3)
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with self.assertRaises(auth.AuthorizationError):
                live.seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard,
                                  authorization=approved, authority=self.authority.authority, delivery_authorization=self.delivery)
            conn.commit()
        self.assertEqual(('pending', 0, None, None), self.pending())


    def test_delivery_a_cannot_mutate_or_quarantine_delivery_b(self):
        self.add_live(3, stop=3)
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            approved = self.sealing_approval(conn)
        before = self.pending(3)
        for corrupt in (False, True):
            if corrupt:
                self.sql('UPDATE stop_observations SET reviewer_id=2 WHERE assignment_id=3')
            with connection(self.path, write=True) as conn:
                conn.execute('BEGIN IMMEDIATE')
                with self.assertRaises(auth.AuthorizationError):
                    live.seal_pending(conn, 3, gate=ISSUE, finality_guard=None,
                        authorization=approved, delivery_authorization=self.delivery,
                        authority=self.authority.authority)
                conn.commit()
            self.assertEqual(before, self.pending(3))

    def test_completed_acknowledgement_requires_exact_delivery_binding(self):
        from tests.recognition_authorization_fixture import seal_pending
        self.add_live(3, stop=3)
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard)
            wrong = self.authority.approve(conn, **live.delivery_binding(conn, 3))
            with self.assertRaises(auth.AuthorizationError):
                live.seal_pending(conn, 2, gate=ISSUE, delivery_authorization=wrong,
                                  authority=self.authority.authority)
            right = self.authority.approve(conn, **live.delivery_binding(conn, 2))
            self.assertTrue(live.seal_pending(conn, 2, gate=ISSUE, delivery_authorization=right,
                                             authority=self.authority.authority)['idempotent'])
            conn.commit()

    def test_caught_claim_failure_then_commit_leaves_no_partial_operation(self):
        from tests.recognition_authorization_fixture import seal_pending
        before = self.sql('SELECT operation_id FROM recognition_private_operations')
        original = permanent.check_claim_integrity
        def fail(conn, stop):
            if stop == 2:
                raise RuntimeError('synthetic-claim-failure')
            return original(conn, stop)
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with patch.object(permanent, 'check_claim_integrity', side_effect=fail):
                with self.assertRaises(RuntimeError):
                    seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard)
            conn.commit()
        self.assertEqual(before, self.sql('SELECT operation_id FROM recognition_private_operations'))
        self.assertEqual(('pending', 0, None, None), self.pending())
        self.assertEqual([], self.sql('SELECT * FROM recognition_first_look_claims WHERE physical_stop_id=2'))


    def test_retry_action_cannot_replay_approval_for_other_delivery(self):
        self.add_live(3, stop=3)
        before = self.pending(3)
        error = sqlite3.OperationalError('synthetic-busy')
        error.sqlite_errorcode = sqlite3.SQLITE_BUSY
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            binding = {**live.delivery_binding(conn, 2), 'action': 'record_retryable_failure'}
            approved = self.authority.approve(conn, **binding)
            with self.assertRaises(auth.AuthorizationError):
                live.record_retryable_failure(conn, 3, error, gate=ISSUE,
                    authorization=approved, authority=self.authority.authority)
            conn.commit()
        self.assertEqual(before, self.pending(3))

    def test_authority_failure_after_insertion_rolls_back_even_if_caller_commits(self):
        from tests.recognition_authorization_fixture import seal_pending
        from src.review.recognition import authority as provision
        original_check = provision.check_authority
        original_integrity = permanent.check_claim_integrity
        failed = [False]
        def after_insert(conn, stop):
            result = original_integrity(conn, stop)
            if stop == 2:
                failed[0] = True
            return result
        def unavailable(handle, approved):
            if failed[0]:
                raise permanent.Quarantined('synthetic-authority-unavailable')
            original_check(handle, approved)
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            with patch.object(permanent, 'check_claim_integrity', side_effect=after_insert), \
                 patch.object(provision, 'check_authority', side_effect=unavailable):
                with self.assertRaises(auth.AuthorizationError):
                    seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard)
            conn.commit()
        self.assertEqual(('pending', 0, None, None), self.pending())
        self.assertEqual([(1,)], self.sql('SELECT COUNT(*) FROM recognition_private_operations'))

    def test_frozen_live_decision_cannot_be_issued_through_historical_writer(self):
        from tests.recognition_authorization_fixture import sealing_binding
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            decision = self.guard(conn, {'configuration': asdict(live_fixture.CONFIG)})
            prepared = permanent._prepare(conn, 'first_look', decision['inputs'],
                                          decision['evaluation_at_utc'], decision['reference'])
        prepared['format'] = 'live-first-look-operation-v1'
        with self.assertRaisesRegex(ValueError, 'historical_manifest_required'):
            permanent.finalize(self.path, prepared, manifest_sha256=digest(prepared),
                               authorization_reference=decision['reference'], gate=ISSUE)
        for helper in ('_insert_operation', '_insert_first_look_claim'):
            with self.subTest(helper=helper), self.assertRaises(AttributeError):
                getattr(permanent, helper)


    def test_live_and_migration_writers_reject_caller_selected_authority(self):
        from src.review.recognition.authority import Authority
        error = sqlite3.OperationalError('synthetic-busy')
        error.sqlite_errorcode = sqlite3.SQLITE_BUSY
        before = self.pending()
        with connection(self.path, write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            issuance = self.sealing_approval(conn)
            capture = self.authority.approve(conn, **auth.admission_binding(asdict(live_fixture.CONFIG)))
            retry = self.authority.approve(conn, **{
                **live.delivery_binding(conn, 2), 'action': 'record_retryable_failure'})
            for impostor in (lambda _: True, object.__new__(Authority)):
                calls = [
                    lambda: live.enqueue(conn, 2, configuration=live_fixture.CONFIG, gate=CAPTURE,
                                         authorization=capture, authority=impostor),
                    lambda: live.seal_pending(conn, 2, gate=ISSUE, finality_guard=self.guard,
                        authorization=issuance, delivery_authorization=self.delivery, authority=impostor),
                    lambda: live.record_retryable_failure(conn, 2, error, gate=ISSUE,
                                                         authorization=retry, authority=impostor),
                ]
                for call in calls:
                    with self.assertRaises(auth.AuthorizationError):
                        call()
                for module, family, definitions in (
                    (permanent_schema, 'private_recognition', permanent_schema.definitions()),
                    (live_first_look_schema, 'first_look', live_first_look_schema.OBJECTS)):
                    approval = self.authority.approve(conn, **auth.migration_binding(family, definitions))
                    with self.assertRaises(auth.AuthorizationError):
                        module.install(conn, authorization=approval, authority=impostor)
            conn.commit()
        self.assertEqual(before, self.pending())

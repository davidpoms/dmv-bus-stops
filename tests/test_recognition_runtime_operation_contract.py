"""4a detached contracts using real 2c -> 3a -> 3b, disposable storage only."""

from copy import deepcopy
from contextlib import ExitStack
from dataclasses import replace
import sqlite3
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, dependencies, events, operations
from src.review.recognition import runtime_operation_contract as c, runtime_validation as v
from src.review.recognition import runtime_profile_schema as r, writer_boundary, local_execution, local_readiness
from src.review.recognition.authorization import AuthorizationError
from src.review.recognition.rules import canonical, digest
from tests import test_recognition_runtime_authentication as lifecycle
from tests import test_recognition_administration as f


class RuntimeOperationContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lifecycle.RuntimeAuthenticationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.config = self.fixture.config
        self.primary = self.fixture.primary()
        self.session = self.fixture.session(self.primary)
        self.assertEqual(3, self.fixture.validate(self.primary, self.session).generation)
        self.creation = dict(request_id=str(uuid4()), request_sha256=digest({'review': 'proposal'}),
            actor_id=1, primary_sha256=a.token_hash(self.primary), session_sha256=a.token_hash(self.session))
        # Generate new detached data from the actual runtime snapshot, never
        # rewrite/adopt an old persisted console preparation.
        request = dict(family='first_look', inputs=deepcopy(self.fixture.f.operation['envelope']['provenance']['inputs']), evaluation_at_utc=f.at(900),
            review_reference='proposal', preparer_id='1', generation_reference=f.INSTALLATION+':3', parent_event_id=None)
        with a.connect(self.config.target) as target:
            target.execute('BEGIN')
            target.execute('PRAGMA query_only=ON')
            manifest = events._generate(target, request)
            p = dict(format='recognition-preparation-v1', preparation_id=str(uuid4()), request=request,
                generated_at_utc=f.at(900), generator='permanent._prepare:v1',
                target_observation=a.observe_target(target)['observation'], manifest=manifest,
                manifest_sha256=digest(manifest), population_sha256=digest(manifest['candidates']),
                dependencies=dependencies.build(target, manifest))
        e = dict(format='recognition-event-v1', event_id=str(uuid4()), preparation_id=p['preparation_id'],
            preparation_sha256=digest(p), parent_event_id=None, frozen_at_utc=f.at(900))
        self.frozen = dict(preparation=p, event=e)
        self.operation_id = str(uuid4())

    def build(self, context, **kwargs):
        return c.build_operation(context, frozen=kwargs.pop('frozen', self.frozen), operation_id=self.operation_id,
            creation=kwargs.pop('creation', self.creation), created_at_utc=kwargs.pop('created_at_utc', f.at(900)), **kwargs)

    def test_real_lifecycle_canonical_target_and_envelope_round_trip(self):
        with v.authentication_transaction(self.config) as context:
            target = c.build_target(context)
            self.assertEqual(c.TARGET_FIELDS, set(target))
            self.assertEqual(target, c.parse_target(canonical(target), context=context))
            c.require_same_target(target, deepcopy(target), context=context)
            envelope = self.build(context)
            self.assertEqual(envelope, c.parse_operation(canonical(envelope), context=context,
                frozen=self.frozen, operation_sha256=digest(envelope)))
            self.assertEqual(c.OPERATION_FORMAT, envelope['format'])
            self.assertEqual(c.ENVELOPE_FIELDS, set(envelope))
            self.assertEqual(self.frozen['preparation']['target_observation'], envelope['target_observation'])
            self.assertNotEqual(self.fixture.original_identity(self.config.target).hostname,
                                envelope['target_observation']['hostname'])
            self.assertNotIn('operation_sha256', envelope)
            self.assertEqual(digest(envelope), digest(c.parse_operation(canonical(envelope), context=context,
                frozen=self.frozen, operation_sha256=digest(envelope))))

    def test_exact_fields_missing_extra_and_nested_identity_claims(self):
        with v.authentication_transaction(self.config) as context:
            good = c.build_target(context)
            for key in good:
                bad = dict(good); del bad[key]
                with self.subTest(missing=key), self.assertRaises(ValueError): c.validate_target(bad, context=context)
            for key in ('hostname', 'device', 'inode', 'target_schema_sha256', 'authority'):
                with self.subTest(extra=key), self.assertRaises(ValueError):
                    c.validate_target(dict(good, **{key: 'claim'}), context=context)

    def test_canonical_types_uuid_sha_boolean_float_and_nul(self):
        with v.authentication_transaction(self.config) as context:
            target = c.build_target(context)
            cases = [('installation_id', 'not-uuid'), ('target_id', f.INSTALLATION.upper()),
                ('binding_sha256', 'A'*64), ('runtime_profile_sha256', 'g'*64),
                ('binding_sha256', '0'*64+'\0'), ('binding_sha256','0'*31+'\0'+'0'*32),
                ('installation_id', target['installation_id']+'\0')]
            cases += [(key, value) for key in ('generation','owner_id','auth_epoch','mfa_epoch')
                      for value in (True, False, 1.0, '1', 0, -1, 2**63)]
            for key, value in cases:
                with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                    c.validate_target(dict(target, **{key:value}), context=context)

    def test_every_otherwise_canonical_scope_mismatch(self):
        with v.authentication_transaction(self.config) as context:
            target = c.build_target(context)
            for key in target.keys() - {'format'}:
                value = target[key]
                wrong = str(uuid4()) if key.endswith('_id') and type(value) is str else (
                    '0'*64 if type(value) is str else value+1)
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'target_mismatch:'+key):
                    c.validate_target(dict(target, **{key:wrong}), context=context)

    def test_noncanonical_duplicate_json_and_floating_json(self):
        with v.authentication_transaction(self.config) as context:
            target = c.build_target(context)
            for serialized in (canonical(target)+' ', canonical(target).replace('"generation":3', '"generation":3.0'),
                               canonical(target)[:-1]+',"generation":3}'):
                with self.subTest(serialized=serialized), self.assertRaises(ValueError):
                    c.parse_target(serialized, context=context)

    def test_operation_target_scope_mismatch_with_recomputed_envelope_digest(self):
        with v.authentication_transaction(self.config) as context:
            good=self.build(context)
            for key in c.TARGET_FIELDS-{'format'}:
                target=deepcopy(good['local_target'])
                value=target[key]
                target[key]=str(uuid4()) if key in ('installation_id','target_id') else (
                    '0'*64 if type(value) is str else value+1)
                changed=dict(good,local_target=target)
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'target_mismatch:'+key):
                    c.validate_operation(changed,context=context,frozen=self.frozen,operation_sha256=digest(changed))

    def test_large_profile_device_inode_are_lossless_and_not_duplicated(self):
        huge=2**80
        original=self.fixture.original_identity
        def hardware(subject):
            return replace(original(subject),device=huge,inode=huge+1)
        # As in 3a's large-integer rehearsal, every observation alias must see
        # consistent synthetic hardware from deployment through enrollment.
        with ExitStack() as stack:
            for module in list(sys.modules.values()):
                if (getattr(module,'__name__','').startswith('src.review.recognition')
                        and getattr(module,'target_identity',None) is original):
                    stack.enter_context(patch.object(module,'target_identity',side_effect=hardware))
            stack.enter_context(patch.object(a,'target_identity',side_effect=hardware))
            fixture=lifecycle.RuntimeAuthenticationTests()
            try:
                fixture.setUp()
                with v.authentication_transaction(fixture.config) as context:
                    target=c.build_target(context)
                    observation=dict(hostname='synthetic-web',database=str(fixture.config.target),device=huge+1,inode=huge+1)
                    c._physical(observation,context=context)
                    self.assertNotIn('device',target)
                    self.assertNotIn('inode',target)
                    self.assertEqual(target,c.parse_target(canonical(target),context=context))
            finally:
                fixture.doCleanups()

    def test_no_forged_cached_or_retired_context(self):
        with v.authentication_transaction(self.config) as context:
            target = c.build_target(context)
        for wrong in (context, target, None):
            with self.subTest(context=type(wrong)), self.assertRaises((a.AdminError,ValueError,TypeError)):
                c.validate_target(target, context=wrong)

    def test_actual_runtime_identity_mismatch_and_final_drift(self):
        with patch.object(a, 'target_identity', side_effect=self.fixture.original_identity):
            with self.assertRaisesRegex(a.AdminError, 'identity_mismatch'):
                with v.authentication_transaction(self.config) as context: c.build_target(context)
        with patch.object(a, 'target_identity', side_effect=self.fixture.runtime_identity) as observation:
            with self.assertRaisesRegex(a.AdminError, 'identity_mismatch'):
                with v.authentication_transaction(self.config) as context:
                    c.build_target(context)
                    observation.side_effect = self.fixture.original_identity

    def test_profile_pointer_not_current_and_history_corruption(self):
        with a.connect(self.config.control) as conn:
            from src.review.recognition.trust import load
            body = load(conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=3').fetchone()[0])
        for key, value in (('runtime_profile_sha256', None), ('runtime_profile_sha256','0'*64),
                           ('previous_sha256','0'*64)):
            changed = dict(body, **{key:value})
            self.fixture.sql('DROP TRIGGER recognition_admin_bindings_immutable_update')
            self.fixture.sql('UPDATE recognition_admin_bindings SET body_json=?,body_sha256=? WHERE generation=3',
                             (canonical(changed),digest(changed)))
            self.fixture.sql(a.schema.definitions()['recognition_admin_bindings_immutable_update'])
            with self.subTest(key=key,value=value), self.assertRaises((a.AdminError,ValueError)):
                with v.authentication_transaction(self.config) as context: c.build_target(context)

    def test_profile_content_corruption_is_not_just_matching_digest_string(self):
        self.fixture.sql('DROP TRIGGER '+r.PROFILES+'_immutable_update')
        self.fixture.sql(f"UPDATE {r.PROFILES} SET target_inode=target_inode||'0'")
        self.fixture.sql(r.definitions()[r.PROFILES+'_immutable_update'])
        with self.assertRaisesRegex(ValueError, 'digest_mismatch'):
            with v.authentication_transaction(self.config) as context: c.build_target(context)

    def test_legacy_formats_rejected_even_with_recomputed_digest(self):
        with v.authentication_transaction(self.config) as context:
            good = self.build(context)
            for format in (operations.CONTRACT, operations.ENROLLED_CONTRACT, operations.LOCAL_CONTRACT, 'unknown'):
                wrong = dict(good, format=format)
                with self.subTest(format=format), self.assertRaisesRegex(ValueError, 'legacy_or_unknown'):
                    c.validate_operation(wrong, context=context, frozen=self.frozen, operation_sha256=digest(wrong))

    def test_operation_and_provenance_mutation_with_recomputed_digest(self):
        with v.authentication_transaction(self.config) as context:
            good = self.build(context)
            for key, value in (('provenance', dict(good['provenance'], review_reference='changed')),
                ('dependencies_sha256','0'*64), ('writer_manifest_sha256','0'*64), ('rule_sha256','0'*64),
                ('population_sha256','0'*64), ('action','execute'), ('member_ids',[]), ('operation_version',True)):
                wrong = dict(good, **{key:value})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    c.validate_operation(wrong, context=context, frozen=self.frozen, operation_sha256=digest(wrong))
            changed = dict(good, creation=dict(good['creation'], request_sha256='0'*64))
            with self.assertRaisesRegex(ValueError, 'operation_digest_mismatch'):
                c.validate_operation(changed, context=context, frozen=self.frozen, operation_sha256=digest(good))
            with self.assertRaises(ValueError):
                c.validate_operation(dict(good,operation_sha256=digest(good)), context=context,
                    frozen=self.frozen, operation_sha256=digest(good))

    def test_creation_provenance_scope_and_parent(self):
        other = self.fixture.primary()
        with v.authentication_transaction(self.config) as context:
            for key, value in (('actor_id',2), ('primary_sha256',a.token_hash(other)),
                               ('session_sha256','0'*64), ('request_id',str(uuid4())+'\0')):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    self.build(context,creation=dict(self.creation, **{key:value}))

    def test_runtime_observation_mutation_not_console_substitution(self):
        with v.authentication_transaction(self.config) as context:
            for key, value in (('hostname','console'), ('database','/wrong/path'), ('device',1), ('inode',1),
                               ('device',True), ('inode',1.0), ('hostname','web\0')):
                frozen = deepcopy(self.frozen)
                frozen['preparation']['target_observation'][key] = value
                frozen['event']['preparation_sha256'] = digest(frozen['preparation'])
                with self.subTest(key=key,value=value), self.assertRaises(ValueError): self.build(context,frozen=frozen)

    def test_frozen_corruption_recomputed_links_and_canonical_time(self):
        with v.authentication_transaction(self.config) as context:
            for path, value in ((('preparation','dependencies','sha256'),'0'*64),
                                (('preparation','request','generation_reference'),'wrong:3'),
                                (('event','preparation_sha256'),'0'*64),
                                (('preparation','request','inputs'),{'unexpected':1.5})):
                frozen = deepcopy(self.frozen)
                subject = frozen
                for key in path[:-1]: subject = subject[key]
                subject[path[-1]] = value
                if path[0]=='preparation': frozen['event']['preparation_sha256']=digest(frozen['preparation'])
                with self.subTest(path=path), self.assertRaises(ValueError): self.build(context,frozen=frozen)
            for time in ('2099-01-01T00:15:00+00:00',f.at(900)+'\0',f.at(899)):
                with self.subTest(time=time), self.assertRaises(ValueError): self.build(context,created_at_utc=time)

    def test_nested_utc_is_canonical_even_with_recomputed_all_digest_links(self):
        with v.authentication_transaction(self.config) as context:
            cutoff=self.frozen['preparation']['manifest']['inputs']['cutoff_utc']
            for changed in (cutoff[:-1]+'+00:00',None,f.at(901)):
                frozen=deepcopy(self.frozen)
                p=frozen['preparation']
                p['manifest']['inputs']['cutoff_utc']=changed
                p['request']['inputs']['cutoff_utc']=changed
                p['manifest_sha256']=digest(p['manifest'])
                p['dependencies']['manifest_sha256']=digest(p['manifest'])
                p['dependencies']['sha256']=digest({k:value for k,value in p['dependencies'].items() if k!='sha256'})
                frozen['event']['preparation_sha256']=digest(p)
                with self.subTest(cutoff=changed),self.assertRaisesRegex(ValueError,'invalid_time|noncanonical_time|evaluation_before_cutoff'):
                    self.build(context,frozen=frozen)

    def test_contracts_neither_write_nor_read_key_nor_grant_authority(self):
        before = (self.config.target.read_bytes(),self.config.control.read_bytes())
        original = v._authentication_writes
        def deny_write(action,*args):
            if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                self.fail('4a attempted a database write')
            return original(action,*args)
        with patch.object(v,'_authentication_writes',side_effect=deny_write), \
             patch.object(lifecycle.auth,'_cipher',side_effect=AssertionError('key access')):
            with v.authentication_transaction(self.config) as context:
                envelope = self.build(context)
                c.validate_operation(envelope,context=context,frozen=self.frozen,operation_sha256=digest(envelope))
                with self.assertRaises(AuthorizationError): writer_boundary.acquire(envelope,self.config.target,{})
                result=local_execution.execute_approved_operation(envelope,self.session,'unused',now=f.at(900))
                self.assertEqual(('BLOCKED','NOT_STARTED'),(result.admission,result.state))
        self.assertFalse(local_readiness.assess(self.config,now=f.at(900))['activation_ready'])
        self.assertEqual(before,(self.config.target.read_bytes(),self.config.control.read_bytes()))

    def test_revoked_creation_references_are_historical_not_authentication(self):
        self.fixture.sql('UPDATE recognition_admin_sessions SET revoked=1')
        with self.assertRaises(a.AdminError): self.fixture.validate(self.primary,self.session)
        with v.authentication_transaction(self.config) as context:
            envelope=self.build(context)
            self.assertEqual(self.creation,envelope['creation'])
            with self.assertRaises(AuthorizationError): writer_boundary.acquire(envelope,self.config.target,{})


if __name__ == '__main__':
    unittest.main()

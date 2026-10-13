"""Ephemeral keys and new SQLite fixtures only; no deployment artifacts or services."""

import base64
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import os
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.review.recognition import artifacts as a, authorization as auth, authority
from src.review.recognition.rules import canonical, digest


NOW = '2026-10-13T12:00:00Z'
EARLIER = '2026-10-13T11:59:00Z'
EXPIRY = '2026-10-13T12:05:00Z'


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        # Never persist a private key. No production keys or identities are loaded.
        self.key = Ed25519PrivateKey.generate()
        self.trust = dict(keys=[dict(key_id='synthetic-key', issuer_id='synthetic-issuer',
            public_key=base64.b64encode(self.key.public_key().public_bytes_raw()).decode('ascii'),
            grants=[dict(approver_id='synthetic-reviewer', family=f, permission=p, action=x,
                         max_lifetime_seconds=600) for f, p, x in sorted(a.MATRIX)])],
            host_id='synthetic-host', deployment_id='synthetic-deployment',
            revocation_registry_id='synthetic-registry', max_registry_age_seconds=120,
            minimum_registry_sequence=1)
        self.verifier = a.SyntheticArtifactVerifier(canonical(self.trust))
        self.addCleanup(self.verifier.cleanup)
        self.path = self.verifier.directory / 'synthetic.db'
        sqlite3.connect(self.path).close()
        observed, parent = self.path.stat(), self.path.parent.stat()
        self.enrollment = dict(enrollment_id='synthetic-enrollment', enrollment_generation=1,
            environment='production', host_id='synthetic-host', hostname=socket.gethostname(),
            database_absolute_path=str(self.path), device=observed.st_dev, inode=observed.st_ino,
            parent_directory_absolute_path=str(self.path.parent), parent_device=parent.st_dev,
            parent_inode=parent.st_ino, required_link_count=1, deployment_id='synthetic-deployment',
            reference='synthetic-independent-enrollment-review', issuer_id='synthetic-issuer',
            issued_at_utc=EARLIER)
        self.enrollment_sha256 = digest(self.enrollment)
        self.registry = dict(registry_id='synthetic-registry', sequence=1,
            issued_at_utc=EARLIER, expires_at_utc=EXPIRY, revoked_approvals=[],
            revoked_issuers=[], revoked_keys=[], revoked_enrollments=[], revoked_deployments=[])
        self.binding = dict(auth.migration_binding('private_recognition', {'synthetic': 'schema'}),
            rule_sha256=None, manifest_sha256=None,
            snapshot_sha256=None, reference='synthetic-review',
            evidence={'prerequisite_schema_sha256': digest('synthetic-prerequisite')})
        self.payload = dict(approval_id='synthetic-approval', issuer_id='synthetic-issuer',
            approver_id='synthetic-reviewer', environment='production',
            enrollment_id=self.enrollment['enrollment_id'], enrollment_generation=1,
            enrollment_sha256=self.enrollment_sha256,
            target=dict(hostname=socket.gethostname(), database=str(self.path),
                        device=observed.st_dev, inode=observed.st_ino),
            deployment_id='synthetic-deployment', **deepcopy(self.binding), issued_at_utc=EARLIER,
            not_before_utc=EARLIER, expires_at_utc=EXPIRY,
            revocation_registry_id='synthetic-registry', minimum_revocation_sequence=1,
            usage={'mode': 'exact_operation', 'integrity_only_retries': True})
        self.expected_binding_json = canonical(self.binding)

    def envelope(self, payload=None, key=None):
        payload = deepcopy(self.payload if payload is None else payload)
        signature = (key or self.key).sign(a.canonical_payload_bytes(canonical(payload)))
        return dict(format=a.FORMAT, algorithm=a.ALGORITHM, key_id='synthetic-key',
                    payload=payload, signature=base64.b64encode(signature).decode('ascii'))

    def verify(self, artifact=None, **overrides):
        return a.validate_artifact(canonical(self.envelope()) if artifact is None else artifact,
            **dict(dict(enrollment_json=canonical(self.enrollment),
                enrollment_sha256=self.enrollment_sha256, enrollment_id='synthetic-enrollment',
                enrollment_generation=1, expected_binding_json=self.expected_binding_json,
                trusted_now_utc=NOW, registry_json=canonical(self.registry), verifier=self.verifier),
                **overrides))

    def enrollment_check(self, value=None, **overrides):
        value = self.enrollment if value is None else value
        return a.validate_enrollment(canonical(value), **dict(dict(expected_sha256=self.enrollment_sha256,
            enrollment_id='synthetic-enrollment', enrollment_generation=1,
            trusted_now_utc=NOW, verifier=self.verifier), **overrides))

    def test_valid_signature_enrollment_and_no_database_reads_or_mutations(self):
        before = self.path.read_bytes()
        with patch.object(sqlite3, 'connect', side_effect=AssertionError('no SQL in validator')):
            result = self.verify()
            self.assertEqual(result.sha256, digest(json.loads(result.canonical_json)))
            self.assertEqual(digest(self.enrollment), self.enrollment_check().sha256)
        self.assertEqual(before, self.path.read_bytes())

    def test_canonical_bytes_are_explicit_and_preserve_existing_helpers(self):
        reordered = dict(reversed(list(self.payload.items())))
        expected = a.DOMAIN + canonical(self.payload).encode('utf-8')
        self.assertEqual(expected, a.canonical_payload_bytes(json.dumps(reordered, indent=2)))
        env = self.envelope()
        self.verify(json.dumps(dict(reversed(list(env.items()))), indent=2))
        self.assertEqual('{"a":1,"z":"\\u00e9"}', canonical({'z': '\u00e9', 'a': 1}))
        env['signature'] = base64.b64encode(self.key.sign(
            json.dumps(self.payload, indent=2).encode())).decode()
        with self.assertRaisesRegex(auth.AuthorizationError, 'signature'):
            self.verify(canonical(env))

    def test_duplicate_keys_at_every_depth_and_invalid_json_numbers(self):
        raw = canonical(self.envelope())
        for changed in (raw.replace('"format":', '"format":"duplicate","format":', 1),
                        raw.replace('"approval_id":', '"approval_id":"x","approval_id":', 1),
                        raw.replace('"hostname":', '"hostname":"x","hostname":', 1),
                        raw.replace('"mode":', '"mode":"x","mode":', 1)):
            with self.subTest(raw=changed[:20]), self.assertRaisesRegex(auth.AuthorizationError, 'duplicate'):
                self.verify(changed)
        for token in ('NaN', 'Infinity', '-Infinity', '1e999', '1.0'):
            with self.subTest(token=token), self.assertRaises(auth.AuthorizationError):
                self.verify(raw.replace('"minimum_revocation_sequence":1',
                                        '"minimum_revocation_sequence":' + token))

    def test_every_envelope_and_payload_field_is_required_and_unknowns_rejected(self):
        original = self.envelope()
        for location in ('envelope', 'payload'):
            fields = a.ENVELOPE if location == 'envelope' else a.PAYLOAD
            for field in (*sorted(fields), 'unknown'):
                value = deepcopy(original)
                target = value if location == 'envelope' else value['payload']
                if field == 'unknown':
                    target[field] = 'extra'
                else:
                    del target[field]
                with self.subTest(location=location, field=field), self.assertRaises(auth.AuthorizationError):
                    self.verify(canonical(value))

    def test_custom_objects_and_callback_substitution_rejected(self):
        class Accepting(dict):
            def __call__(self, *args):
                return True
        for value in ({}, Accepting(), lambda *args: True, object(), b'{}'):
            with self.subTest(value=type(value)), self.assertRaises(auth.AuthorizationError):
                self.verify(value)
        for value in (None, Accepting(), lambda *args: True, object()):
            with self.subTest(context=type(value)), self.assertRaisesRegex(
                    auth.AuthorizationError, 'production_trust_configuration_unavailable'):
                self.verify(verifier=value)
        with self.assertRaises(TypeError):
            self.verify(authorization_verifier=lambda *args: True)

    def test_signature_key_id_algorithm_and_format_substitution(self):
        for field, value in (('signature', 'bad'), ('signature', 'AA=='),
                             ('signature', base64.b64encode(bytes(64)).decode()),
                             ('key_id', 'unknown'), ('algorithm', 'none'),
                             ('algorithm', 'HS256'), ('format', 'production-approval-v1')):
            env = self.envelope()
            env[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(auth.AuthorizationError):
                self.verify(canonical(env))
        with self.assertRaisesRegex(auth.AuthorizationError, 'signature'):
            self.verify(canonical(self.envelope(key=Ed25519PrivateKey.generate())))
        env = self.envelope()
        env['payload']['reference'] = 'tampered'
        with self.assertRaisesRegex(auth.AuthorizationError, 'signature'):
            self.verify(canonical(env))

    def test_replaced_pinned_key_and_alternate_domain_cannot_verify(self):
        trust = deepcopy(self.trust)
        trust['keys'][0]['public_key'] = base64.b64encode(
            Ed25519PrivateKey.generate().public_key().public_bytes_raw()).decode()
        verifier = a.SyntheticArtifactVerifier(canonical(trust))
        self.addCleanup(verifier.cleanup)
        with self.assertRaisesRegex(auth.AuthorizationError, 'signature'):
            self.verify(verifier=verifier)
        env = self.envelope()
        env['signature'] = base64.b64encode(self.key.sign(
            b'other-domain\x00' + canonical(self.payload).encode())).decode()
        with self.assertRaisesRegex(auth.AuthorizationError, 'signature'):
            self.verify(canonical(env))

    def test_signed_identity_and_binding_substitution(self):
        for field, value in (('issuer_id', 'forged'), ('approver_id', 'forged'),
                ('environment', 'disposable'), ('enrollment_id', 'other'),
                ('enrollment_generation', 2), ('enrollment_sha256', '0' * 64),
                ('deployment_id', 'other'), ('reference', 'other'),
                ('operation_sha256', '0' * 64), ('policy_sha256', '0' * 64),
                ('revocation_registry_id', 'other'), ('minimum_revocation_sequence', 10)):
            value_payload = {**self.payload, field: value}
            with self.subTest(field=field), self.assertRaises(auth.AuthorizationError):
                self.verify(canonical(self.envelope(value_payload)))
        for field, value in (('hostname', 'other'), ('database', str(self.path.with_name('other.db'))),
                             ('device', self.path.stat().st_dev + 1), ('inode', self.path.stat().st_ino + 1)):
            payload = deepcopy(self.payload)
            payload['target'][field] = value
            with self.subTest(target=field), self.assertRaisesRegex(auth.AuthorizationError, 'target'):
                self.verify(canonical(self.envelope(payload)))

    def test_wrong_types_hashes_and_nested_fields(self):
        for field, value in (('enrollment_generation', True), ('minimum_revocation_sequence', False),
                ('minimum_revocation_sequence', -1), ('approval_id', []), ('issuer_id', ''),
                ('operation_sha256', 'A' * 64), ('policy_sha256', 'invalid'),
                ('enrollment_sha256', None), ('rule_sha256', '0' * 64), ('population_sha256', '0' * 64),
                ('manifest_sha256', '0' * 64), ('snapshot_sha256', '0' * 64),
                ('usage', {'mode': 'exact_operation', 'integrity_only_retries': 1}),
                ('evidence', {'prerequisite_schema_sha256': 'bad'}),
                ('target', {**self.payload['target'], 'extra': True})):
            with self.subTest(field=field), self.assertRaises(auth.AuthorizationError):
                self.verify(canonical(self.envelope({**self.payload, field: value})))

    def test_lifetime_ordering_expiry_future_and_malformed_timestamps(self):
        cases = [('expires_at_utc', NOW), ('not_before_utc', '2026-10-13T12:01:00Z'),
                 ('issued_at_utc', '2026-10-13T12:01:00Z'), ('expires_at_utc', EARLIER),
                 ('expires_at_utc', '2099-01-01T00:00:00Z')]
        for field in ('issued_at_utc', 'not_before_utc', 'expires_at_utc'):
            cases.extend((field, value) for value in (None, 'bad', '2026-10-13T12:00:00+00:00',
                '2026-1-1T00:00:00Z', '2026-10-13T12:00:00.000Z', '2026-02-30T00:00:00Z'))
        for field, value in cases:
            with self.subTest(field=field, value=value), self.assertRaises(auth.AuthorizationError):
                self.verify(canonical(self.envelope({**self.payload, field: value})))

    def test_clock_rollback_and_no_default_clock(self):
        self.verify()
        with self.assertRaisesRegex(auth.AuthorizationError, 'clock_rollback'):
            self.verify(trusted_now_utc=EARLIER)
        with self.assertRaises(auth.AuthorizationError):
            self.verify(trusted_now_utc=lambda: NOW)

    def test_enrollment_clock_is_stateless_and_rejects_future_issuance(self):
        self.verify()  # Artifact history now contains NOW.
        self.enrollment_check(trusted_now_utc=EARLIER)
        with self.assertRaisesRegex(auth.AuthorizationError, 'enrollment_future_issuance'):
            self.enrollment_check(trusted_now_utc='2026-10-13T11:58:59Z')
        # Standalone enrollment calls did not reset the artifact clock history.
        with self.assertRaisesRegex(auth.AuthorizationError, 'trusted_clock_rollback'):
            self.verify(trusted_now_utc=EARLIER)

    def test_unicode_escapes_normalization_and_surrogate_signature_behavior(self):
        for reference in ('caf\u00e9', 'cafe\u0301', 'surrogate-\ud800'):
            payload = deepcopy(self.payload)
            payload['reference'] = reference
            expected = json.loads(self.expected_binding_json)
            expected['reference'] = reference
            expected = canonical(expected)
            env = self.envelope(payload)
            escaped = json.dumps(env, ensure_ascii=True)
            literal = json.dumps(env, ensure_ascii=False)
            with self.subTest(reference=ascii(reference)):
                first = self.verify(escaped, expected_binding_json=expected)
                second = self.verify(literal, expected_binding_json=expected)
                self.assertEqual(first, second)
                self.assertEqual(env['signature'], self.envelope(payload)['signature'])
                self.assertEqual(reference, json.loads(first.canonical_json)['payload']['reference'])
        composed = {**self.payload, 'reference': 'caf\u00e9'}
        decomposed = {**self.payload, 'reference': 'cafe\u0301'}
        self.assertNotEqual(a.canonical_payload_bytes(json.dumps(composed)),
                            a.canonical_payload_bytes(json.dumps(decomposed)))
        env = self.envelope(composed)
        env['payload'] = decomposed  # Preserve the original signature.
        with self.assertRaisesRegex(auth.AuthorizationError, 'artifact_signature_invalid'):
            self.verify(json.dumps(env))
        # Python str JSON accepts a lone surrogate, but raw strict UTF-8 does not.
        with self.assertRaises(UnicodeEncodeError):
            'surrogate-\ud800'.encode('utf-8')
        self.assertIn(b'\\ud800', a.canonical_payload_bytes(
            json.dumps({**self.payload, 'reference': 'surrogate-\ud800'})))

    def test_original_expectations_do_not_follow_nested_candidate_mutation(self):
        self.assertIsNot(self.payload['evidence'], self.binding['evidence'])
        self.payload['evidence']['prerequisite_schema_sha256'] = digest('changed')
        self.assertEqual(json.loads(self.expected_binding_json), self.binding)
        with self.assertRaisesRegex(auth.AuthorizationError, 'artifact_binding_mismatch'):
            self.verify()
        candidate = {**self.enrollment, 'issuer_id': 'changed-enrollment-issuer'}
        with self.assertRaisesRegex(auth.AuthorizationError, 'enrollment_hash_mismatch'):
            self.enrollment_check(candidate)

    def test_revoked_approval_issuer_key_enrollment_and_deployment(self):
        fields = {'revoked_approvals': 'synthetic-approval', 'revoked_issuers': 'synthetic-issuer',
                  'revoked_keys': 'synthetic-key', 'revoked_enrollments': 'synthetic-enrollment',
                  'revoked_deployments': 'synthetic-deployment'}
        for index, (field, value) in enumerate(fields.items(), 2):
            registry = {**self.registry, 'sequence': index, field: [value]}
            with self.subTest(field=field), self.assertRaisesRegex(auth.AuthorizationError, 'revoked'):
                self.verify(registry_json=canonical(registry))

    def test_registry_unavailable_stale_rollback_equivocation_and_malformed(self):
        for registry in (None, '{}', canonical({**self.registry, 'sequence': True}),
                canonical({**self.registry, 'issued_at_utc': '2026-10-13T11:00:00Z'}),
                canonical({**self.registry, 'expires_at_utc': NOW}),
                canonical({**self.registry, 'revoked_keys': 'not-a-list'})):
            with self.subTest(registry=registry), self.assertRaises(auth.AuthorizationError):
                self.verify(registry_json=registry)
        self.verify(registry_json=canonical({**self.registry, 'sequence': 2}))
        with self.assertRaisesRegex(auth.AuthorizationError, 'rollback'):
            self.verify()
        with self.assertRaisesRegex(auth.AuthorizationError, 'equivocation'):
            self.verify(registry_json=canonical({**self.registry, 'sequence': 2, 'revoked_keys': ['other']}))

    def test_malformed_trust_and_no_payload_selected_roles(self):
        variants = [{}, {**self.trust, 'extra': True}, {**self.trust, 'keys': []},
                    {**self.trust, 'max_registry_age_seconds': 0}]
        for field, value in (('public_key', 'invalid'), ('key_id', ''), ('grants', [])):
            trust = deepcopy(self.trust)
            trust['keys'][0][field] = value
            variants.append(trust)
        trust = deepcopy(self.trust)
        trust['keys'][0]['grants'][0]['max_lifetime_seconds'] = True
        variants.append(trust)
        for trust in variants:
            with self.subTest(trust=trust.keys()), self.assertRaises(auth.AuthorizationError):
                a.SyntheticArtifactVerifier(canonical(trust))
        # A correctly signed action is still denied when absent from key grants.
        trust = deepcopy(self.trust)
        trust['keys'][0]['grants'] = [g for g in trust['keys'][0]['grants'] if g['action'] != 'install']
        verifier = a.SyntheticArtifactVerifier(canonical(trust))
        self.addCleanup(verifier.cleanup)
        with self.assertRaisesRegex(auth.AuthorizationError, 'not_authorized'):
            self.verify(verifier=verifier)

    def test_enrollment_all_fields_required_unknowns_and_malformed(self):
        for field in (*sorted(a.ENROLLMENT), 'extra'):
            value = dict(self.enrollment)
            if field == 'extra':
                value[field] = 1
            else:
                del value[field]
            with self.subTest(field=field), self.assertRaises(auth.AuthorizationError):
                self.enrollment_check(value)
        raw = canonical(self.enrollment).replace('"environment":', '"environment":"x","environment":')
        with self.assertRaisesRegex(auth.AuthorizationError, 'duplicate'):
            a.validate_enrollment(raw, expected_sha256=digest(self.enrollment),
                enrollment_id='synthetic-enrollment', enrollment_generation=1,
                trusted_now_utc=NOW, verifier=self.verifier)

    def test_enrollment_expected_identity_and_unavailable_context(self):
        for arguments in ({'enrollment_id': 'other'}, {'enrollment_generation': 2},
                          {'enrollment_generation': True}, {'verifier': None}):
            with self.subTest(arguments=arguments), self.assertRaises(auth.AuthorizationError):
                self.enrollment_check(**arguments)
        closed = a.SyntheticArtifactVerifier(canonical(self.trust))
        closed.cleanup()
        with self.assertRaisesRegex(auth.AuthorizationError, 'configuration_unavailable'):
            self.verify(verifier=closed)

    def test_enrollment_identity_and_environment_mismatches(self):
        for field, value in (('environment', 'disposable'), ('hostname', 'wrong'), ('host_id', 'wrong'),
                ('deployment_id', 'wrong'), ('enrollment_generation', 2), ('enrollment_generation', True),
                ('device', self.enrollment['device'] + 1), ('inode', self.enrollment['inode'] + 1),
                ('parent_device', self.enrollment['parent_device'] + 1),
                ('parent_inode', self.enrollment['parent_inode'] + 1), ('required_link_count', 2),
                ('required_link_count', True), ('database_absolute_path', 'relative.db'),
                ('database_absolute_path', str(self.path.with_name('absent.db'))),
                ('parent_directory_absolute_path', str(self.path.parent.parent))):
            with self.subTest(field=field), self.assertRaises(auth.AuthorizationError):
                self.enrollment_check({**self.enrollment, field: value})
        with self.assertRaisesRegex(auth.AuthorizationError, 'hash'):
            self.enrollment_check(expected_sha256='0' * 64)

    def test_replaced_inode_rejected(self):
        replacement = self.path.with_name('replacement.db')
        sqlite3.connect(replacement).close()
        old_inode = self.path.stat().st_ino
        os.replace(replacement, self.path)
        self.assertNotEqual(old_inode, self.path.stat().st_ino)
        with self.assertRaisesRegex(auth.AuthorizationError, 'identity'):
            self.enrollment_check()

    def test_real_hardlink_rejected_against_original_identity(self):
        link = self.path.with_name('hardlink.db')
        os.link(self.path, link)
        with self.assertRaisesRegex(auth.AuthorizationError, 'identity'):
            self.enrollment_check()

    def test_directory_replacing_target_rejected(self):
        self.path.unlink()
        self.path.mkdir()
        with self.assertRaisesRegex(auth.AuthorizationError, 'regular_file'):
            self.enrollment_check()

    def test_symlink_target_rejected(self):
        link = self.path.with_name('symlink.db')
        try:
            link.symlink_to(self.path)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows identity lacks symlink privilege')
            raise
        # Structural alias check: this separate candidate intentionally has its own
        # hash. The ancestor test below instead preserves a previously valid path.
        candidate = {**self.enrollment, 'database_absolute_path': str(link)}
        with self.assertRaisesRegex(auth.AuthorizationError, 'alias'):
            self.enrollment_check(candidate, expected_sha256=digest(candidate))

    def nested_enrollment(self):
        parent = self.verifier.directory / 'nested'
        parent.mkdir()
        target = parent / 'synthetic.db'
        sqlite3.connect(target).close()
        file_stat, parent_stat = target.stat(), parent.stat()
        expected = {**self.enrollment, 'database_absolute_path': str(target),
            'device': file_stat.st_dev, 'inode': file_stat.st_ino,
            'parent_directory_absolute_path': str(parent),
            'parent_device': parent_stat.st_dev, 'parent_inode': parent_stat.st_ino}
        frozen_hash = digest(expected)
        self.enrollment_check(expected, expected_sha256=frozen_hash)
        return parent, target, expected, frozen_hash

    def test_real_ancestor_symlink_rejected_against_original_identity(self):
        parent, target, expected, frozen_hash = self.nested_enrollment()
        with tempfile.TemporaryDirectory(prefix='recognition-alias-test-') as directory:
            outside = Path(directory).resolve()
            self.assertFalse(outside.is_relative_to(self.verifier.directory))
            sqlite3.connect(outside / target.name).close()
            alias = self.verifier.directory / 'alias-capability-probe'
            try:
                alias.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                if getattr(error, 'winerror', None) == 1314:
                    self.skipTest('Windows identity lacks directory symlink privilege')
                raise
            alias.unlink()
            saved = self.verifier.directory / 'original-parent'
            self.assertTrue(parent.resolve().is_relative_to(self.verifier.directory))
            self.assertTrue(saved.parent.resolve() == self.verifier.directory)
            parent.rename(saved)
            parent.symlink_to(outside, target_is_directory=True)
            try:
                with self.assertRaisesRegex(auth.AuthorizationError, 'enrollment_alias_rejected'):
                    self.enrollment_check(expected, expected_sha256=frozen_hash)
            finally:
                parent.unlink()  # Remove our link, never the external directory.

    def test_real_parent_replacement_preserves_file_but_rejects_parent(self):
        parent, target, expected, frozen_hash = self.nested_enrollment()
        replacement = self.verifier.directory / 'replacement-parent'
        saved = self.verifier.directory / 'original-parent'
        replacement.mkdir()
        for path in (parent, replacement, saved):
            self.assertTrue(path.parent.resolve() == self.verifier.directory)
        self.assertNotEqual(replacement.stat().st_ino, expected['parent_inode'])
        parent.rename(saved)
        replacement.rename(parent)
        # Preserve the real file inode, so only the independently pinned parent
        # changes. A copied replacement file would mask the parent-specific guard.
        (saved / target.name).rename(target)
        self.assertEqual(target.stat().st_ino, expected['inode'])
        with self.assertRaisesRegex(auth.AuthorizationError, 'enrollment_parent_identity_mismatch'):
            self.enrollment_check(expected, expected_sha256=frozen_hash)

    def test_outside_workspace_rejected_before_target_stat(self):
        other = a.SyntheticArtifactVerifier(canonical(self.trust))
        self.addCleanup(other.cleanup)
        with self.assertRaisesRegex(auth.AuthorizationError, 'workspace'):
            self.enrollment_check(verifier=other)

    def test_alias_rejection_does_not_depend_on_symlink_creation_privilege(self):
        # Exercise both alias guards even on Windows accounts that cannot create links.
        for method in ('is_symlink', 'is_junction'):
            if not hasattr(Path, method):
                continue
            original = getattr(Path, method)
            def alias(path):
                return path == self.path or original(path)
            with self.subTest(method=method), patch.object(Path, method, alias), \
                    self.assertRaisesRegex(auth.AuthorizationError, 'alias'):
                self.enrollment_check()

    def test_nested_input_mutation_cannot_change_result_or_pinned_trust(self):
        result = self.verify()
        saved = result.canonical_json
        self.trust['keys'][0]['issuer_id'] = 'changed'
        self.verify()
        self.payload['evidence']['prerequisite_schema_sha256'] = '0' * 64
        self.enrollment['inode'] += 1
        copy = json.loads(result.canonical_json)
        copy['payload']['target']['inode'] += 1
        self.assertEqual(saved, result.canonical_json)
        with self.assertRaises(FrozenInstanceError):
            result.sha256 = '0' * 64

    def test_valid_artifact_is_not_writer_authority_and_crossover_fails(self):
        result = self.verify()
        with self.assertRaisesRegex(auth.AuthorizationError, 'authorization_required'):
            auth.verify(self.path, result, self.verifier)
        with self.assertRaisesRegex(auth.AuthorizationError, 'production_authority_not_provisioned'):
            authority.provision_production_authority()
        workspace = authority.DisposableWorkspace()
        self.addCleanup(workspace.cleanup)
        database = Path(workspace.name) / 'synthetic.db'
        sqlite3.connect(database).close()
        binding = auth.migration_binding('private_recognition', {'synthetic': 'schema'})
        approval = workspace.approve(database, **binding)
        auth.verify(database, approval, workspace.authority, **binding)
        production = auth.Authorization(target=auth.target_identity(self.path), environment='production',
            reference='synthetic-only', **binding)
        workspace.approved.add(production)
        with self.assertRaises(auth.AuthorizationError):
            auth.verify(self.path, production, workspace.authority, **binding)
        with self.assertRaises(auth.AuthorizationError):
            auth.verify(database, approval, result, **binding)
        # A disposable target cannot be adopted by the synthetic enrollment verifier.
        candidate = {**self.enrollment, 'database_absolute_path': str(database),
                     'parent_directory_absolute_path': str(database.parent)}
        # Structural containment test, with the separate candidate's hash explicit.
        with self.assertRaisesRegex(auth.AuthorizationError, 'workspace'):
            self.enrollment_check(candidate, expected_sha256=digest(candidate))

    def test_all_matrix_actions_and_nullable_fields(self):
        for family, permission, action in sorted(a.MATRIX):
            with self.subTest(family=family, action=action):
                payload = deepcopy(self.payload)
                payload.update(family=family, permission=permission, action=action,
                    rule_sha256=digest('rule'), policy_sha256=digest('rule'),
                    operation_sha256=digest('operation'), population_sha256=digest('population'),
                    manifest_sha256=digest('operation'), snapshot_sha256=None)
                payload['evidence'] = {'review_package_sha256': digest('review')}
                if action == 'enqueue':
                    config = dict(activation_at_utc=EARLIER, historical_cutoff_utc=EARLIER,
                                  policy_reference='synthetic-review', policy_sha256=digest('policy'),
                                  sqlite_utc_provenance=None)
                    payload.update(auth.admission_binding(config), manifest_sha256=None)
                    payload['evidence'] = {k: config[k] for k in a.EVIDENCE[action]}
                    payload['usage'] = dict(mode='bounded_capture', starts_at_utc=EARLIER, ends_at_utc=EXPIRY)
                elif action == 'install':
                    payload.update(deepcopy(self.binding))
                    payload['family'] = family
                elif action == 'process_delivery':
                    payload.update(manifest_sha256=None, evidence={'assignment_id': 1})
                elif action == 'approve_closed_population':
                    payload['evidence'] = dict(historical_operation_id=digest('baseline'),
                        historical_qualified_sha256=digest('qualified'), activation_at_utc=EARLIER,
                        frontier_at_utc=NOW, gap_assignment_ids=[], baseline_link_review_reference='synthetic-link')
                elif action == 'seal_pending':
                    payload['evidence'] = dict(finality_approval_id='synthetic-finality',
                                               delivery_approval_id='synthetic-delivery')
                if family == 'geography_steward':
                    payload['snapshot_sha256'] = digest('snapshot')
                    payload['evidence'].update(certification_approval_ids=['synthetic-cert'], evaluation_at_utc=NOW)
                # This positive matrix checks structural self-consistency, not
                # independent manifest preparation. Freeze its baseline BEFORE
                # mutations; negative candidates never regenerate the expectation.
                expected = canonical(deepcopy({k: payload[k] for k in a.BINDINGS}))
                self.verify(canonical(self.envelope(payload)), expected_binding_json=expected)
                for field in ('operation_sha256', 'policy_sha256', 'rule_sha256',
                              'population_sha256', 'manifest_sha256', 'snapshot_sha256'):
                    if payload[field] is not None:
                        changed = deepcopy(payload)
                        changed[field] = digest('changed-binding')
                        with self.subTest(changed_hash=field), self.assertRaises(auth.AuthorizationError):
                            self.verify(canonical(self.envelope(changed)), expected_binding_json=expected)
                for field in ('rule_sha256', 'population_sha256', 'manifest_sha256', 'snapshot_sha256'):
                    changed = deepcopy(payload)
                    changed[field] = digest('wrong') if payload[field] is None else None
                    with self.subTest(field=field), self.assertRaises(auth.AuthorizationError):
                        self.verify(canonical(self.envelope(changed)), expected_binding_json=expected)

    def test_dependent_revocation_and_exact_expected_evidence_types(self):
        payload = deepcopy(self.payload)
        payload.update(family='first_look', permission='issuance', action='seal_pending',
            rule_sha256=digest('rule'), manifest_sha256=payload['operation_sha256'],
            population_sha256=digest('population'),
            evidence={'finality_approval_id': 'synthetic-finality', 'delivery_approval_id': 'synthetic-delivery'})
        expected = canonical({k: payload[k] for k in a.BINDINGS})
        with self.assertRaisesRegex(auth.AuthorizationError, 'dependency_revoked'):
            self.verify(canonical(self.envelope(payload)), expected_binding_json=expected,
                        registry_json=canonical({**self.registry, 'revoked_approvals': ['synthetic-finality']}))
        payload.update(action='process_delivery', manifest_sha256=None, evidence={'assignment_id': 1})
        expected = {k: payload[k] for k in a.BINDINGS}
        expected['evidence'] = {'assignment_id': True}
        with self.assertRaisesRegex(auth.AuthorizationError, 'binding_mismatch'):
            self.verify(canonical(self.envelope(payload)), expected_binding_json=canonical(expected))

    def test_import_is_inert_and_has_no_writer_integration(self):
        import subprocess
        import sys
        code = '''
from unittest.mock import patch
with patch('sqlite3.connect', side_effect=AssertionError('SQL')), \\
     patch('tempfile.TemporaryDirectory', side_effect=AssertionError('workspace')), \\
     patch('src.review.recognition.authority.provision_production_authority', side_effect=AssertionError('authority')):
    import src.review.recognition.artifacts
'''
        result = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)


class IndependentSignatureVectorTests(unittest.TestCase):
    def test_fixed_vector_and_one_byte_message_mutation(self):
        # Prepared once outside repository helpers using an ephemeral test key and
        # independently serialized JSON. The private key was discarded. No signing,
        # fixture artifact builder, or implementation DOMAIN is used for this vector.
        payload_json = (
            '{"action":"install","approval_id":"vector-approval","approver_id":"vector-reviewer",'
            '"deployment_id":"vector-deployment","enrollment_generation":1,"enrollment_id":"vector-enrollment",'
            '"enrollment_sha256":"e07fda620aa86c800709a5a78e218bb68728c7f9448cfb9f9de4ff93443dfd76",'
            '"environment":"production","evidence":{"prerequisite_schema_sha256":'
            '"2222222222222222222222222222222222222222222222222222222222222222"},'
            '"expires_at_utc":"2026-10-13T12:05:00Z","family":"private_recognition",'
            '"issued_at_utc":"2026-10-13T11:59:00Z","issuer_id":"vector-issuer","manifest_sha256":null,'
            '"minimum_revocation_sequence":1,"not_before_utc":"2026-10-13T11:59:00Z",'
            '"operation_sha256":"1111111111111111111111111111111111111111111111111111111111111111",'
            '"permission":"migration",'
            '"policy_sha256":"1111111111111111111111111111111111111111111111111111111111111111",'
            '"population_sha256":null,"reference":"vector-review","revocation_registry_id":"vector-registry",'
            '"rule_sha256":null,"snapshot_sha256":null,"target":{"database":"/synthetic/vector.db",'
            '"device":1,"hostname":"vector-host","inode":2},'
            '"usage":{"integrity_only_retries":true,"mode":"exact_operation"}}'
        )
        message = b'DMV-recognition-synthetic-approval-v1\x00' + payload_json.encode('ascii')
        public_key = bytes.fromhex('efb7d22b26103200fc9424e6bdd0ee62e39b1fb11bb07744538c6e89d500e747')
        signature = bytes.fromhex(
            '38cf232dccb62f39e677e7ae759b68106599300ef12bb4bf8ac449dca7fc0eaf3'
            '72c6a401e8c4013e726c226dfadc8233e2ab32a335f5b3b952619da262a5501')
        self.assertEqual(message, a.canonical_payload_bytes(payload_json))
        trust = dict(keys=[dict(key_id='vector-key', issuer_id='vector-issuer',
            public_key=base64.b64encode(public_key).decode(), grants=[dict(
                approver_id='vector-reviewer', family='private_recognition', permission='migration',
                action='install', max_lifetime_seconds=600)])], host_id='vector-host',
            deployment_id='vector-deployment', revocation_registry_id='vector-registry',
            max_registry_age_seconds=120, minimum_registry_sequence=1)
        verifier = a.SyntheticArtifactVerifier(json.dumps(trust))
        self.addCleanup(verifier.cleanup)
        enrollment_json = (
            '{"database_absolute_path":"/synthetic/vector.db","deployment_id":"vector-deployment",'
            '"device":1,"enrollment_generation":1,"enrollment_id":"vector-enrollment",'
            '"environment":"production","host_id":"vector-host","hostname":"vector-host","inode":2,'
            '"issued_at_utc":"2026-10-13T11:59:00Z","issuer_id":"vector-issuer","parent_device":1,'
            '"parent_directory_absolute_path":"/synthetic","parent_inode":3,'
            '"reference":"vector-enrollment-review","required_link_count":1}'
        )
        enrollment_hash = 'e07fda620aa86c800709a5a78e218bb68728c7f9448cfb9f9de4ff93443dfd76'
        self.assertEqual(enrollment_hash, digest(json.loads(enrollment_json)))
        expected = dict(family='private_recognition', permission='migration', action='install',
            operation_sha256='1' * 64, policy_sha256='1' * 64, rule_sha256=None,
            population_sha256=None, manifest_sha256=None, snapshot_sha256=None,
            reference='vector-review', evidence={'prerequisite_schema_sha256': '2' * 64})
        registry = dict(registry_id='vector-registry', sequence=1, issued_at_utc=EARLIER,
            expires_at_utc=EXPIRY, revoked_approvals=[], revoked_issuers=[], revoked_keys=[],
            revoked_enrollments=[], revoked_deployments=[])
        kwargs = dict(enrollment_json=enrollment_json, enrollment_sha256=enrollment_hash,
            enrollment_id='vector-enrollment', enrollment_generation=1,
            expected_binding_json=json.dumps(expected), trusted_now_utc=NOW,
            registry_json=json.dumps(registry), verifier=verifier)
        envelope = dict(format='recognition-synthetic-approval-v1', algorithm='Ed25519',
            key_id='vector-key', payload=json.loads(payload_json), signature=base64.b64encode(signature).decode())
        # Only filesystem enrollment is stubbed: a fixed vector cannot contain a
        # platform's random temporary pathname/inode. Real signature verification,
        # canonicalization, grants, lifetime and binding comparisons are NOT mocked.
        with patch.object(a, 'validate_enrollment', return_value=a.ValidatedArtifact(
                enrollment_json, enrollment_hash)) as enrollment_check:
            result = a.validate_artifact(json.dumps(envelope), **kwargs)
            self.assertEqual('vector-approval', json.loads(result.canonical_json)['payload']['approval_id'])
            enrollment_check.assert_called_once_with(enrollment_json,
                expected_sha256=enrollment_hash, enrollment_id='vector-enrollment',
                enrollment_generation=1, trusted_now_utc=NOW, verifier=verifier)
            changed = payload_json.replace('vector-review"', 'vector-reviex"')
            self.assertEqual(1, sum(x != y for x, y in zip(payload_json, changed)))
            envelope['payload'] = json.loads(changed)
            with self.assertRaisesRegex(auth.AuthorizationError, 'artifact_signature_invalid'):
                a.validate_artifact(json.dumps(envelope), **kwargs)
            self.assertEqual(1, enrollment_check.call_count)  # Failed before filesystem check.


if __name__ == '__main__':
    unittest.main()

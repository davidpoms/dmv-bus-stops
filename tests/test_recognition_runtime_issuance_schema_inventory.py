"""Z15 inventory scope only. No lifecycle attempt, metadata owner or writer."""

from contextlib import contextmanager, ExitStack
from dataclasses import fields, FrozenInstanceError
import os
from pathlib import Path
import pickle
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import runtime_issuance_schema_inventory as preparation
from src.review.recognition import administration_schema as schema
from src.review.recognition import runtime_execution_coordinator as coordinator
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition import runtime_execution_attempt_schema as attempts
from src.review.recognition import runtime_enrollment_transition_schema as transitions
from tests import test_recognition_runtime_coordinator_final_validation_profile as g2
from tests import test_recognition_runtime_target_entry_owner as support


@contextmanager
def writable_test_directories():
    """F7/F9's test-only allocation correction, never permission repair."""
    original = tempfile.mkdtemp
    root = Path(__file__).resolve().parents[1]
    def allocate(suffix=None, prefix=None, dir=None):
        if dir is not None or prefix not in (None, 'recognition-disposable-'):
            return original(suffix=suffix, prefix=prefix, dir=dir)
        directory = root / ((prefix or 'z15-preview-')+uuid4().hex+(suffix or ''))
        os.mkdir(directory, 0o777)
        return str(directory)
    with patch.object(tempfile, 'mkdtemp', allocate):
        yield


class IssuanceSchemaInventoryTests(unittest.TestCase):
    def test_opaque_unregistered_failure_and_fresh_fallback(self):
        with self.assertRaises(TypeError):
            preparation._Preparation()
        shell = object.__new__(preparation._Preparation)
        with self.assertRaises(TypeError):
            pickle.dumps(shell)
        self.assertFalse(hasattr(shell, '__dict__'))
        for name in ('execute', 'connection', 'commit', 'writer', 'authority', 'create_attempt'):
            self.assertFalse(hasattr(shell, name))
        with self.assertRaises(ValueError):
            preparation._mint(object(), {})
        with self.assertRaises(ValueError):
            preparation._check(object(), shell)
        with sqlite3.connect(':memory:') as connection:
            connection.execute('CREATE TABLE first(value TEXT)')
            first = schema._control_objects(connection)
            connection.execute('CREATE TABLE second(value TEXT)')
            self.assertNotEqual(first, schema._control_objects(connection))

    def test_genuine_g2_issuance_inventory_only_and_fresh_relationships(self):
        # No validator, ownership registry, clock, consent or activation verifier
        # is replaced. The existing fixture supplies synthetic activation data.
        with writable_test_directories():
            config, session, confirmation, approval_id, options = g2.CoordinatorFinalValidationProfileTests.prepare_g2(self)
        captured = []
        mint = preparation._mint
        finish = preparation._final_validation
        original_objects = preparation._objects
        reused = [0]
        migrations = [0]
        control_checks = [0]
        original_manifest = transitions.historical_manifest
        original_control = schema.check_control

        def minted(context, artifact):
            state = coordinator._state(context)
            before = (state.control.total_changes, state.target.total_changes)
            mint(context, artifact)
            facts = state.issuance_inventory
            self.assertIs(type(facts), preparation._Facts)
            self.assertEqual(before, (state.control.total_changes, state.target.total_changes))
            self.assertIs(facts.context, context)
            self.assertIs(facts.owner[-1], state.outer)
            self.assertIs(facts.phase, state.phase_id)
            self.assertEqual(facts.connections, state.connections)
            self.assertEqual(facts.epochs, state.epochs)
            self.assertTrue(all(type(row) is tuple and len(row)==2 for row in facts.objects))
            self.assertFalse(any('migration' in item.name for item in fields(facts)))
            with self.assertRaises(FrozenInstanceError):
                facts.objects = ()
            with self.assertRaises(TypeError):
                pickle.dumps(facts.preparation)
            with self.assertRaises(ValueError):
                preparation._check(object(), facts.preparation)
            captured.append((state, facts))

        def objects(connection):
            if preparation._active.get() is not None:
                reused[0] += 1
            return original_objects(connection)

        def manifest(*args, **kwargs):
            if preparation._active.get() is not None:
                migrations[0] += 1
            return original_manifest(*args, **kwargs)

        def control(*args, **kwargs):
            if preparation._active.get() is not None:
                control_checks[0] += 1
            return original_control(*args, **kwargs)

        @contextmanager
        def final(state):
            with finish(state):
                if state.issuance_inventory is not None:
                    facts = state.issuance_inventory
                    self.assertEqual(facts.objects, preparation._check(state.context, facts.preparation))
                    # A forged object cannot substitute even in the same context.
                    with self.assertRaises(ValueError):
                        preparation._check(state.context, object.__new__(preparation._Preparation))
                    # A malformed migration relationship must still fail even
                    # while the exact prepared inventory is accepted.
                    rows = issuer.storage._rows
                    def missing_migration(conn, action):
                        if action == transitions.ACTION:
                            return []
                        return rows(conn, action)
                    with patch.object(issuer.storage, '_rows', side_effect=missing_migration):
                        with self.assertRaisesRegex(ValueError, 'transition_migration_audit'):
                            transitions.historical_manifest(state.control)
                yield

        with ExitStack() as patches:
            for module, name, replacement in (
                (preparation, '_mint', minted), (preparation, '_final_validation', final),
                (preparation, '_objects', objects), (transitions, 'historical_manifest', manifest),
                (schema, 'check_control', control),
            ):
                patches.enter_context(patch.object(module, name, replacement))
            for module, name in ((support.writer_boundary, 'acquire'),
                                 (support.execution, 'execute_operation'),
                                 (support.local_execution, 'execute_approved_operation'),
                                 (support.permanent, 'finalize')):
                patches.enter_context(patch.object(module, name, side_effect=AssertionError('downstream authority')))
            with coordinator.coordinator(config, session, confirmation, approval_id, **options):
                self.assertEqual(1, len(captured))
                state, facts = captured[0]
                self.assertIsNone(state.issuance_inventory)
                with self.assertRaises(ValueError):
                    preparation._check(facts.context, facts.preparation)
        self.assertGreater(reused[0], 0)
        self.assertGreater(migrations[0], 0)
        self.assertGreater(control_checks[0], 0)
        with support.a.connect(config.control) as control, support.a.connect(config.target) as target:
            self.assertEqual(0, control.execute(f'SELECT count(*) FROM {attempts.ATTEMPTS}').fetchone()[0])
            row = control.execute(f'SELECT issued_at,expires_at FROM {issuer.storage.AUTHORITIES}').fetchone()
            self.assertEqual(120, row['expires_at']-row['issued_at'])
            for table in ('recognition_execution_claims', 'recognition_execution_seals', 'recognition_operation_receipts', support.storage.TABLE):
                self.assertEqual(0, target.execute('SELECT count(*) FROM '+table).fetchone()[0])

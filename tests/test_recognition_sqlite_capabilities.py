"""Capability rejection and transactional preservation; disposable databases only."""

from contextlib import contextmanager
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import administration as a, runtime_profile_schema as r
from src.review.recognition import sqlite_capabilities as capabilities
from tests import test_recognition_administration as fixture
from tests.recognition_production_owner_fixture import allocation


class OperatorConnection:
    def __init__(self, conn, missing):
        self.conn, self.missing = conn, missing

    def execute(self, sql, *args):
        if sql == 'SELECT ? '+self.missing+' ?':
            raise sqlite3.OperationalError('near ">": syntax error')
        return self.conn.execute(sql, *args)


class CapabilityTests(unittest.TestCase):
    def test_supported_runtime_preserves_large_inode_text(self):
        result = capabilities.inspect_runtime()
        self.assertTrue(result['supported'], result)
        self.assertEqual({'->': True, '->>': True}, result['operators'])

    def test_each_missing_operator_fails_closed(self):
        with sqlite3.connect(':memory:') as conn:
            for operator in ('->', '->>'):
                with self.subTest(operator=operator):
                    wrapped = OperatorConnection(conn, operator)
                    self.assertFalse(capabilities.inspect_connection(wrapped)['supported'])
                    with self.assertRaisesRegex(ValueError, capabilities.ERROR):
                        capabilities.require_runtime_profile(wrapped)

    def test_diagnostic_opens_only_memory(self):
        original = sqlite3.connect
        with patch.object(capabilities.sqlite3, 'connect', wraps=original) as connect:
            capabilities.inspect_runtime()
        connect.assert_called_once_with(':memory:')


class MigrationCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(allocation())
        self.f = fixture.AdministrationTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.f.confirmation()

    def migrate(self):
        return a.migrate_runtime_profile_contract(self.f.config, expected_generation=1,
            operator='fixture', reason='capability test', now=fixture.at(60))

    def assert_preserved(self, before):
        self.assertEqual(before, (self.f.control.read_bytes(), self.f.path.read_bytes()))
        self.assertEqual(1, a.get_installation_control(self.f.config)['generation'])
        with a.connect(self.f.control) as conn:
            self.assertFalse(conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (r.CHALLENGES,)).fetchone())

    def test_unsupported_preflight_precedes_all_extension_ddl(self):
        before = (self.f.control.read_bytes(), self.f.path.read_bytes())
        original = capabilities.inspect_connection
        with patch.object(capabilities, 'inspect_connection',
                side_effect=lambda conn: original(OperatorConnection(conn, '->'))), \
                patch.object(r, 'definitions', side_effect=AssertionError('extension DDL reached')):
            with self.assertRaisesRegex(ValueError, capabilities.ERROR):
                self.migrate()
        self.assert_preserved(before)

    def test_supported_preflight_continues_migration(self):
        with patch.object(capabilities, 'require_runtime_profile', wraps=capabilities.require_runtime_profile) as check:
            self.assertEqual(2, self.migrate())
        check.assert_called_once()

    def test_ddl_failure_after_created_objects_rolls_back_everything(self):
        before = (self.f.control.read_bytes(), self.f.path.read_bytes())
        original = a.connect
        reached = []

        @contextmanager
        def injected(path, **kwargs):
            with original(path, **kwargs) as conn:
                if path != self.f.control or not kwargs.get('write'):
                    yield conn
                    return
                class FailingConnection:
                    def __getattr__(self, name):
                        return getattr(conn, name)

                    def execute(self, sql, *args):
                        if sql.startswith('CREATE TRIGGER recognition_runtime_profile_challenge_guard '):
                            reached.append(bool(conn.execute('SELECT 1 FROM sqlite_master WHERE name=?',
                                (r.CHALLENGES,)).fetchone()))
                            raise sqlite3.OperationalError('near ">": syntax error')
                        return conn.execute(sql, *args)
                yield FailingConnection()

        with patch.object(a, 'connect', side_effect=injected):
            with self.assertRaisesRegex(sqlite3.OperationalError, 'syntax error'):
                self.migrate()
        self.assertEqual([True], reached)
        # Byte equality covers schema, binding, generation, audit and every auth row.
        self.assert_preserved(before)

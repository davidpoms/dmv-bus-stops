"""SQL feasibility proof only: synthetic rows, unchanged production definitions."""
import sqlite3
import unittest
from pathlib import Path
from uuid import uuid4

from src.review.recognition import administration as a, administration_schema as schema
from src.review.recognition import runtime_profile_schema as profiles
from src.review.recognition.rules import canonical, digest


class SuccessorStorageTests(unittest.TestCase):
    def test_g5_to_g6_commits_without_ddl_or_constraint_exemptions(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        for sql in {**schema.definitions(), **profiles.definitions()}.values():
            conn.execute(sql)
        ddl = conn.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name').fetchall()
        conn.execute('BEGIN IMMEDIATE')
        installation, target = str(uuid4()), str(uuid4())
        target_path = str((Path.cwd()/'synthetic-target.db').resolve())
        control_path = str((Path.cwd()/'synthetic-control.db').resolve())
        physical = dict(hostname='synthetic-console', database=target_path, device=55, inode=224816447)
        binding = dict(format='recognition-local-control-v2', installation_id=installation,
                       target_id=target, owner_id=144, generation=0, previous_sha256=None,
                       target=dict(observation=physical, schema_sha256='a'*64),
                       control_identity=dict(physical, database=control_path, inode=224805688),
                       production_state='NOT_ACTIVATED', at_utc='2099-01-01T00:00:00Z')
        for generation in range(1, 5):
            binding = dict(binding, generation=generation,
                           previous_sha256=digest(binding) if generation > 1 else None)
            if generation == 4:
                binding.update(format=profiles.V3, runtime_profile_sha256=None)
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',
                         (generation, canonical(binding), digest(binding)))
        preserved = None
        for generation, device, action in ((5, '57', 'synthetic_original_profile'),
                                           (6, '49', 'runtime_profile_device_successor_committed')):
            challenge = dict(challenge_id=str(uuid4()), format='recognition-runtime-enrollment-challenge-v1',
                installation_id=installation, source_generation=generation-1, source_binding_sha256=digest(binding),
                target_id=target, owner_id=144, role='runtime', nonce_sha256=digest(str(uuid4())),
                issued_at=4070908800, expires_at=4070909400, operator='synthetic-owner', reason='SQL proof only',
                audit_sequence=(generation-5)*2+1)
            challenge['challenge_sha256'] = digest(challenge)
            conn.execute(f"INSERT INTO {profiles.CHALLENGES} ({','.join(challenge)}) VALUES ({','.join('?' for _ in challenge)})",
                         tuple(challenge.values()))
            a._audit(conn, 'synthetic_challenge', 'synthetic-owner', '2099-01-01T00:00:00Z',
                     dict(challenge_sha256=challenge['challenge_sha256']))
            profile = dict(format='recognition-runtime-profile-v1', installation_id=installation,
                generation=generation, role='runtime', hostname='synthetic-web',
                target_path=target_path, target_device=device, target_inode='224816447',
                control_path=control_path, control_device=device, control_inode='224805688',
                target_schema_sha256='a'*64, target_id=target, owner_id=144,
                challenge_id=challenge['challenge_id'], observation_sha256=digest(str(uuid4())),
                evidence_channel='operator-reviewed-private-wsgi-log-v1', observed_at=4070908800,
                created_at=4070908800, operator='synthetic-owner', reason='SQL proof only',
                audit_sequence=(generation-5)*2+2)
            profile['profile_sha256'] = digest(profile)
            conn.execute(f"INSERT INTO {profiles.PROFILES} ({','.join(profile)}) VALUES ({','.join('?' for _ in profile)})",
                         tuple(profile.values()))
            binding = dict(binding, generation=generation, previous_sha256=digest(binding),
                           runtime_profile_sha256=profile['profile_sha256'])
            conn.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)',
                         (generation, canonical(binding), digest(binding)))
            a._audit(conn, action, 'synthetic-owner', '2099-01-01T00:00:00Z',
                     dict(profile_sha256=profile['profile_sha256']))
            if generation == 5:
                preserved = tuple(conn.execute(f'SELECT * FROM {profiles.PROFILES} WHERE generation=5').fetchone())
        conn.commit()  # Exercises deferred binding/audit FKs, not merely INSERT admission.
        profiles.check_rows(conn)
        self.assertEqual([], conn.execute('PRAGMA foreign_key_check').fetchall())
        self.assertEqual(preserved, tuple(conn.execute(f'SELECT * FROM {profiles.PROFILES} WHERE generation=5').fetchone()))
        self.assertEqual(ddl, conn.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name').fetchall())
        self.assertEqual([(5, '57'), (6, '49')], [tuple(row) for row in conn.execute(
            f'SELECT generation,target_device FROM {profiles.PROFILES} ORDER BY generation')])

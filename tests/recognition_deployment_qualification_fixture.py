"""Synthetic qualification for owned test stores only; never hosted evidence."""
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

from src.review.recognition import administration as a, deployment_qualification as q
from src.review.recognition.rules import digest
from src.review.recognition.trust import load


def private_files(config):
    # Existing test allocations sometimes deliberately start with permissive
    # modes. This fixture establishes actual private file/parent permissions.
    for path in (config.target, config.control, config.key_file):
        path.chmod(0o600); path.parent.chmod(0o700)


def prepare(test, config, *, now=None, record=True):
    private_files(config)
    directory = test.enterContext(tempfile.TemporaryDirectory(prefix='qualification-backup-'))
    Path(directory).chmod(0o700)
    backups = {}
    for name, source in (('target', config.target), ('control', config.control)):
        destination = Path(directory)/(name+'.db')
        with a.connect(source) as reader:
            writer = sqlite3.connect(destination)
            try:
                reader.backup(writer)
            finally:
                writer.close()
        destination.chmod(0o600)
        backups[name] = str(destination)
    with a.connect(config.control) as control:
        binding = load(control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
    evidence = {key: digest(dict(synthetic_only=key)) for key in q.CHECKS}
    if record:
        # Test fixture setup does not claim a hosted locking experiment. The
        # actual two-process implementation is exercised separately.
        with patch.object(q, 'qualify_locking'):
            q.record(config,operator='synthetic-fixture',reason='test-only qualification',
                     evidence=evidence,backups=backups,expected_generation=binding['generation'],now=now)
    return dict(evidence=evidence, backups=backups, expected_generation=binding['generation'],
                operator='synthetic-fixture', reason='test only', now=now)

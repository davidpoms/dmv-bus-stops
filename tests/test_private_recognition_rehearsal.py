"""CLI safety using synthetic temporary directories, no real cohort or binding."""

from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.active import rehearse_private_recognition as rehearsal
from src.review.recognition.qualification import Quarantined
from src.review.recognition.rules import canonical
from tests import test_recognition_permanent as fixture


class PrivateRehearsalTests(unittest.TestCase):
    sql = fixture.PermanentFamilyTests.sql
    review = fixture.PermanentFamilyTests.review
    first = fixture.PermanentFamilyTests.first

    def setUp(self):
        fixture.PermanentFamilyTests.setUp(self)
        self.review(1)
        self.manifest = self.path.parent / "reviewed.json"
        self.manifest.write_text(canonical(self.first()), encoding="utf-8")
        self.root = self.path.parent / "synthetic-repository"
        self.target = self.root / ".tmp" / "private-recognition-rehearsals" / "disposable-fixture.db"
        root_patch = patch.object(rehearsal, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.kwargs = dict(source=self.path, source_sha256=rehearsal.file_hash(self.path),
                           manifest_path=self.manifest, manifest_sha256=rehearsal.file_hash(self.manifest), target=self.target)

    def run_rehearsal(self, **kwargs):
        return rehearsal.run(**{**self.kwargs, **kwargs})

    def test_verification_default_no_files_or_database_writes(self):
        before = self.path.read_bytes()
        result = self.run_rehearsal()
        self.assertEqual("verification_only", result["mode"])
        self.assertFalse(self.root.exists())
        self.assertEqual(before, self.path.read_bytes())

    def test_wrong_target_hash_and_missing_authorization(self):
        for kwargs in ({"target": self.path}, {"target": self.root / "production.db"},
                       {"source_sha256": "0" * 64}, {"manifest_sha256": "0" * 64},
                       {"apply_disposable": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(Quarantined):
                self.run_rehearsal(**kwargs)
        self.assertFalse(self.target.exists())

    def test_success_retry_exact_source_and_explorer_preservation(self):
        before = self.path.read_bytes()
        kwargs = dict(apply_disposable=True, authorization_reference="synthetic-authorization")
        first = self.run_rehearsal(**kwargs)
        self.assertTrue(first["result"]["issued"])
        self.assertFalse(first["production_authorized"])
        second = self.run_rehearsal(**kwargs, retry_existing=True)
        self.assertTrue(second["result"]["idempotent"])
        self.assertEqual(first["target_sha256"], second["target_sha256"])
        self.assertEqual(before, self.path.read_bytes())
        self.assertTrue(second["explorer_unchanged"])

    def test_failed_sealing_can_retry_disposable_without_source_changes(self):
        kwargs = dict(apply_disposable=True, authorization_reference="synthetic-authorization")
        with patch.object(rehearsal, "finalize", side_effect=Quarantined("synthetic-failure")):
            with self.assertRaises(Quarantined):
                self.run_rehearsal(**kwargs)
        self.assertTrue(self.run_rehearsal(**kwargs, retry_existing=True)["result"]["issued"])
        self.assertEqual(self.kwargs["source_sha256"], rehearsal.file_hash(self.path))

    def test_existing_target_and_receipt_changes_rejected(self):
        kwargs = dict(apply_disposable=True, authorization_reference="synthetic-authorization")
        self.run_rehearsal(**kwargs)
        with self.assertRaisesRegex(Quarantined, "new_disposable_target_required"):
            self.run_rehearsal(**kwargs)
        self.target.with_suffix(".receipt.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(Quarantined, "disposable_receipt_mismatch"):
            self.run_rehearsal(**kwargs, retry_existing=True)


if __name__ == "__main__":
    unittest.main()

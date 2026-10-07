"""Pinned display policy tests; no application database is opened."""
import copy
import json
import socket
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from collections import Counter
from src.dashboard import border_jurisdiction as policy


class BorderJurisdictionTests(unittest.TestCase):
    def setUp(self):
        self.artifact = json.loads(Path(policy.__file__).with_name(
            "border_jurisdiction_policy.json").read_text(encoding="utf-8"))

    def test_population_values_and_deterministic_order(self):
        lookup = policy.validate_policy(self.artifact)
        self.assertEqual(147, len(lookup))
        self.assertEqual(sorted(lookup), list(lookup))
        self.assertEqual({"DC": 82, "MD": 59, None: 6}, Counter(v["value"] for v in lookup.values()))
        self.assertEqual(policy.UNRESOLVED_IDS, {i for i,v in lookup.items() if v["value"] is None})
        self.assertEqual(78, sum(v["border_review_required"] for v in lookup.values()))
        self.assertEqual(lookup, policy.validate_policy(copy.deepcopy(self.artifact)))

    def test_reject_tampered_structure_identity_values_and_hashes(self):
        changes = [
            lambda a: a["stops"].__setitem__(1, copy.deepcopy(a["stops"][0])),
            lambda a: a["stops"][0].__setitem__("value", "VA"),
            lambda a: a["stops"][0].__setitem__("jurisdiction_basis", "standard_geography"),
            lambda a: a.__setitem__("source_report_sha256", "0"*64),
            lambda a: a["stops"][0].__setitem__("physical_stop_id", 999999),
            lambda a: a["stops"].reverse(),
            lambda a: a["stops"][0].__setitem__("value", "DC"),
            lambda a: a["stops"][0].__setitem__("border_notice_reasons", ["invented"]),
        ]
        for change in changes:
            with self.subTest(change=change):
                a=copy.deepcopy(self.artifact); change(a)
                with self.assertRaises(policy.BorderPolicyUnavailable): policy.validate_policy(a)

    def test_lookup_without_io_and_no_successor_inheritance(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("file IO")), \
             patch("builtins.open", side_effect=AssertionError("file IO")), \
             patch.object(sqlite3, "connect", side_effect=AssertionError("database IO")), \
             patch.object(socket, "socket", side_effect=AssertionError("network IO")):
            self.assertIsNone(policy.operational_jurisdiction(999999))
            self.assertIsNone(policy.operational_jurisdiction("6920"))
            self.assertEqual("DC", policy.operational_jurisdiction(545)["value"])
            self.assertEqual("MD", policy.operational_jurisdiction(6920)["value"])
            for i in policy.UNRESOLVED_IDS:
                self.assertIsNone(policy.operational_jurisdiction(i)["value"])
            first=policy.operational_jurisdiction(6920)
            first["border_notice_reasons"].clear()
            self.assertTrue(policy.operational_jurisdiction(6920)["border_review_required"])
            self.assertTrue(policy.operational_jurisdiction(6920)["border_notice_reasons"])

    def test_missing_malformed_policy_fails_closed(self):
        for effect in (FileNotFoundError(), ValueError()):
            with patch.object(Path, "read_text", side_effect=effect):
                self.assertIsNone(policy._load_policy())
        with patch.object(policy, "_POLICY", None):
            for i in (1,545,6920,1064):
                with self.assertRaises(policy.BorderPolicyUnavailable): policy.operational_jurisdiction(i)

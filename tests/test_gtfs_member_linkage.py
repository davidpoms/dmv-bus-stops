import unittest
from src.processing.gtfs_member_linkage import classify_member_links

class LinkageTests(unittest.TestCase):
    def test_exact_outranks_but_preserves_fallback(self):
        rows=classify_member_links("A",[
            {"gtfs_stop_id":"1","stop_code":"A","match_method":"wmata_stop_code"},
            {"gtfs_stop_id":"2","stop_code":"B","match_method":"coordinate"}])
        self.assertEqual(["exact_identity","conflicting_fallback"],[r["linkage_classification"] for r in rows])
        self.assertEqual([True,False],[r["identity_eligible"] for r in rows])
    def test_fallback_without_exact_remains_weaker_eligible(self):
        row=classify_member_links("A",[{"gtfs_stop_id":"2","match_method":"coordinate"}])[0]
        self.assertEqual(("coordinate_fallback",True),(row["linkage_classification"],row["identity_eligible"]))
    def test_multiple_exact_identities_fail_closed(self):
        rows=classify_member_links("A",[
            {"gtfs_stop_id":"1","stop_code":"A","match_method":"wmata_stop_code"},
            {"gtfs_stop_id":"2","stop_code":"A","match_method":"wmata_stop_code"}])
        self.assertTrue(all(r["linkage_classification"]=="unresolved" for r in rows))
        self.assertFalse(any(r["identity_eligible"] for r in rows))
if __name__=="__main__": unittest.main()

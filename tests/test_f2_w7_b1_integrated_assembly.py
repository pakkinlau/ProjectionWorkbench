import unittest

from scripts.run_f2_w7_b1_integrated_assembly import run


class IntegratedCoreRepairShadowSpineTests(unittest.TestCase):
    def test_all_wave6_repairs_and_shadow_spine_cohere(self):
        result = run()
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["terminal"], "INTEGRATED_CORE_REPAIR_SHADOW_SPINE_CANDIDATE_READY")
        self.assertTrue(all(result["checks"].values()))
        self.assertFalse(result["event_spine_cutover_authorized"])
        self.assertFalse(result["canonical_history_rewritten"])


if __name__ == "__main__":
    unittest.main()

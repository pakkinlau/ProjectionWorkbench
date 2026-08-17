import unittest

from scripts.run_f2_w8_b1_lineage_requalification import run


class IntegratedHeadLineageRequalificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run()

    def test_exact_current_head_qualifies(self):
        self.assertTrue(self.result["passed"])
        self.assertEqual(
            self.result["terminal"],
            "CURRENT_HEAD_QUALIFIED_FOR_HUMAN_VALUE_PILOT",
        )
        self.assertEqual(self.result["human_value_pilot_gate"], "OPEN")

    def test_compatibility_model_remains_authoritative(self):
        self.assertFalse(self.result["event_spine_cutover_authorized"])
        self.assertFalse(self.result["canonical_history_rewritten"])
        self.assertTrue(all(self.result["checks"].values()))


if __name__ == "__main__":
    unittest.main()

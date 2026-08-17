from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_f2_w5_b2_independent_redteam.py"
SPEC = importlib.util.spec_from_file_location("f2_w5_b2_redteam", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

class IndependentContributionCapabilityRedTeamTest(unittest.TestCase):
    def test_assessment_is_deterministic_and_finds_current_first_zeros(self) -> None:
        first = MODULE.run()
        second = MODULE.run()
        self.assertEqual(first, second)
        self.assertEqual(first["case_count"], 12)
        self.assertEqual(first["terminal"], "REPAIR_REQUIRED")
        self.assertEqual(first["false_accepts"], 8)
        self.assertEqual(first["false_rejects"], 0)
        self.assertEqual(first["policy_matches"], 4)

if __name__ == "__main__":
    unittest.main()

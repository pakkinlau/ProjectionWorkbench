from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest


def load_runner():
    path = Path("scripts/run_f_ruv_w3q_b5_counterfactual_assignment_requalification.py")
    spec = importlib.util.spec_from_file_location("w3q_b5_runner", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CounterfactualAssignmentRequalificationTests(unittest.TestCase):
    def test_current_integrated_line_returns_lawful_disposition(self):
        result = load_runner().run_requalification()
        self.assertEqual(result["case_count"], 17)
        self.assertTrue(result["counterfactual_surface_requalified"])
        self.assertFalse(result["positive_human_terminal_enabled"])
        self.assertFalse(result["wave_4_open_from_this_branch"])
        self.assertEqual(result["prior_wave_payload_bytes_embedded"], 0)
        self.assertIn(
            result["terminal_disposition"],
            {
                "RIGHT_CENSORED_INTEGRATED_TERMINAL_ADMISSION_OPERAND_ABSENT",
                "COUNTERFACTUAL_ASSIGNMENT_REQUALIFICATION_PASS_AT_INTEGRATED_CONTROLLED_CEILING",
            },
        )


if __name__ == "__main__":
    unittest.main()

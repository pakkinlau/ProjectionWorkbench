from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_f_ruv_w3q_b4_instrumentation_requalification.py"
SPEC = importlib.util.spec_from_file_location("w3q_b4_runner", SCRIPT)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class InstrumentationNoninterferenceIntegratedRequalificationTests(unittest.TestCase):
    def test_current_integrated_line_right_censors_only_missing_b1_materialization(self) -> None:
        result = RUNNER.run(ROOT)
        self.assertEqual(
            result["terminal"],
            "RIGHT_CENSORED_INTEGRATED_TERMINAL_ADMISSION_OPERAND_ABSENT",
        )
        self.assertEqual(result["passed_checks"], 8)
        self.assertEqual(result["failed_checks"], 2)
        failed = [check["check_id"] for check in result["checks"] if not check["passed"]]
        self.assertEqual(
            failed,
            [
                "Q4.09_B1_TERMINAL_ADMISSION_MATERIALIZED",
                "Q4.10_B1_TRANSPORT_CLEARED",
            ],
        )

    def test_b4_mechanical_requalification_is_deterministic_and_nonpromoting(self) -> None:
        first = RUNNER.run(ROOT)
        second = RUNNER.run(ROOT)
        self.assertEqual(first["result_digest"], second["result_digest"])
        self.assertEqual(first["b4_witness_digest"], second["b4_witness_digest"])
        self.assertEqual(first["b4_qualification_terminal"], "INSTRUMENTATION_READY")
        self.assertFalse(first["human_value_supported"])
        self.assertFalse(first["product_direction_authorized"])
        self.assertFalse(first["wave4_open"])

    def test_result_can_be_written_without_repository_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            result = RUNNER.run(ROOT)
            output.write_text(__import__("json").dumps(result, sort_keys=True), encoding="utf-8")
            self.assertTrue(output.is_file())
            self.assertIn("RIGHT_CENSORED", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

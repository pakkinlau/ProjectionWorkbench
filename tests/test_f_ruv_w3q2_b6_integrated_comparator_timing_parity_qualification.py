from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_f_ruv_w3q2_b6_integrated_comparator_timing_parity_qualification.py"
ASSEMBLY_DIR = Path(os.environ.get("W3Q2_ASSEMBLY_DIR", "/tmp/f-ruv-w3q2-b6-assembly"))
PASS_TERMINAL = "INTEGRATED_COMPARATOR_TIMING_PARITY_QUALIFIED_AT_CONTROLLED_FIXTURE_CEILING"
TARGET = "sha256:54ad0ee3651b391ff965fb5bc89954e66e061d4e6ff1e8504d090a6b427e5779"


class IntegratedComparatorTimingParityQualificationTests(unittest.TestCase):
    def run_qualification(self, output: Path) -> dict:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(ROOT),
                "--assembly-dir",
                str(ASSEMBLY_DIR),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return json.loads(output.read_text(encoding="utf-8"))

    def test_exact_target_coordinate_qualifies(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = self.run_qualification(Path(td) / "result.json")
        self.assertEqual(result["terminal_disposition"], PASS_TERMINAL)
        self.assertTrue(result["w3q2_coordinate_passed"])
        self.assertEqual(result["summary"]["failed"], 0)
        self.assertGreaterEqual(result["summary"]["total"], 31)
        self.assertTrue(all(item["pass"] for item in result["qualification_checks"].values()))

    def test_result_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "first.json"
            second = Path(td) / "second.json"
            self.run_qualification(first)
            self.run_qualification(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_target_and_claim_boundaries_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = self.run_qualification(Path(td) / "result.json")
        self.assertEqual(result["target_binding"]["target_identity"], TARGET)
        self.assertEqual(
            result["target_binding"]["target_patch_sha256"],
            result["target_binding"]["observed_patch_sha256"],
        )
        self.assertFalse(result["human_value_supported"])
        self.assertFalse(result["prospective_human_trajectory_authorized"])
        self.assertFalse(result["product_direction_authorized"])
        self.assertFalse(result["wave4_open"])
        self.assertFalse(result["independent_w3q2_complete"])

    def test_noncompensatory_and_tamper_gates_are_exercised(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = self.run_qualification(Path(td) / "result.json")
        checks = result["qualification_checks"]
        required = {
            "Q18_SEQUENCE_GAP_REJECTED",
            "Q19_MONOTONIC_ROLLBACK_REJECTED",
            "Q20_UTC_ROLLBACK_REJECTED",
            "Q21_HASH_CHAIN_TAMPER_REJECTED",
            "Q22_EVENT_ID_TAMPER_REJECTED",
            "Q23_EVENT_CONTENT_TAMPER_REJECTED",
            "Q25_ACTIVE_TIME_BUDGET_FAILS_CLOSED",
            "Q27_GENERIC_BASELINE_CONTAMINATION_REJECTED",
            "Q28_NONCOMPENSATORY_PARITY_FAILURE",
        }
        self.assertTrue(required.issubset(checks))
        self.assertTrue(all(checks[name]["pass"] for name in required))


if __name__ == "__main__":
    unittest.main()

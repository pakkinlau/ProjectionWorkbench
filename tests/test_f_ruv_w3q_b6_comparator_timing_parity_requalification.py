from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_f_ruv_w3q_b6_comparator_timing_parity_requalification.py"
spec = importlib.util.spec_from_file_location("w3q_b6", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ComparatorTimingParityRequalificationTests(unittest.TestCase):
    def test_current_incomplete_snapshot_returns_lawful_right_censor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in (
                "src/repeat_use_harness/custody_repair.py",
                "fixtures/repeat_use/CleanRoomFreshAgentRepair.v1.json",
                "src/repeat_use_harness/noninterference.py",
                "src/repeat_use_harness/counterfactual.py",
                "src/repeat_use_harness/comparator_parity.py",
                "src/repeat_use_harness/replay_integrity.py",
                "scripts/run_f_ruv_w3r_b6_comparator_timing_parity_repair.py",
                "tests/test_f_ruv_w3r_b6_comparator_timing_parity_repair.py",
                "receipts/f_ruv_w3r_b6_execution_receipt.md",
                ".gva-transfer/f-ruv-w3r-b1-payload.part000",
                ".github/workflows/apply-f-ruv-w3r-b1-payload.yml",
            ):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# present\n", encoding="utf-8")
            result = module.inspect_repository(root)
        self.assertEqual(
            result["terminal_disposition"],
            "RIGHT_CENSORED_INTEGRATED_COMPARATOR_REPAIR_OPERAND_ABSENT",
        )
        self.assertEqual(result["missing_components"], ["B1"])
        self.assertFalse(result["wave4_open"])
        self.assertFalse(result["human_value_supported"])
        self.assertEqual(result["branch_completion_predicate"]["result"], "PASS")

    def test_complete_materialization_reaches_only_executable_requalification_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for alternatives in module.COMPONENTS.values():
                target = root / alternatives[0]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# fixture\n", encoding="utf-8")
            for path in module.B6_SURFACES:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# fixture\n", encoding="utf-8")
            result = module.inspect_repository(root)
        self.assertEqual(
            result["terminal_disposition"],
            "READY_FOR_EXECUTABLE_COMPARATOR_TIMING_PARITY_REQUALIFICATION",
        )
        self.assertFalse(result["independent_requalification_complete"])
        self.assertFalse(result["wave4_open"])

    def test_result_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = module.inspect_repository(root)
            second = module.inspect_repository(root)
        self.assertEqual(first["content_digest"], second["content_digest"])


if __name__ == "__main__":
    unittest.main()

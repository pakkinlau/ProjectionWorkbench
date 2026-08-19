from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class IndependentMeasurementValidityReviewTests(unittest.TestCase):
    def test_review_reproduces_repair_terminal_and_all_attack_findings(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "run_f_ruv_w3_b8_independent_measurement_validity_review.py"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(root / "src")
            completed = subprocess.run(
                [sys.executable, str(script), "--output", str(output)],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            review = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(
            review["terminal_disposition"],
            "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_HUMAN_TRAJECTORY",
        )
        self.assertEqual(review["executable_attack_summary"]["cases"], 5)
        self.assertEqual(review["executable_attack_summary"]["confirmed_gaps"], 5)
        self.assertTrue(review["executable_attack_summary"]["passed_as_review"])
        self.assertIn("no live-user", review["claim_ceiling"].lower())


if __name__ == "__main__":
    unittest.main()

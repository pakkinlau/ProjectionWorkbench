from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_f2_w9_b1_human_private_value_pilot import evaluate_pilot, run

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "fixtures" / "human_private_value_pilot" / "pilot.json"


class HumanPrivateValuePilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(INPUT.read_text(encoding="utf-8"))
        self.mechanical = {"passed": True, "terminal": "MECHANICAL_REPAIR_SUPPORTED"}

    def test_real_bound_pilot_is_right_censored_without_human_baseline(self) -> None:
        result = evaluate_pilot(self.payload, self.mechanical, 1.0)
        self.assertEqual(result["terminal"], "RIGHT_CENSORED")
        self.assertTrue(result["passed"])
        self.assertTrue(result["real_project"]["nontrivial"])

    def test_supported_requires_positive_human_confirmation(self) -> None:
        payload = copy.deepcopy(self.payload)
        observation = payload["observation"]
        observation.update({
            "manual_baseline_recorded": True,
            "manual_baseline_minutes": 25,
            "usefulness_confirmed_by_human": True,
            "representation_useful_confirmed_by_human": True,
            "reentry_better_than_baseline_confirmed_by_human": True,
            "capture_review_minutes": 4,
        })
        result = evaluate_pilot(payload, self.mechanical, 1.0)
        self.assertEqual(result["terminal"], "PRIVATE_VALUE_SUPPORTED")

    def test_capture_cost_can_dominate(self) -> None:
        payload = copy.deepcopy(self.payload)
        observation = payload["observation"]
        observation.update({
            "manual_baseline_recorded": True,
            "usefulness_confirmed_by_human": True,
            "representation_useful_confirmed_by_human": True,
            "reentry_better_than_baseline_confirmed_by_human": True,
            "capture_review_minutes": 11,
        })
        result = evaluate_pilot(payload, self.mechanical, 1.0)
        self.assertEqual(result["terminal"], "CAPTURE_COST_TOO_HIGH")

    def test_reentry_must_beat_baseline(self) -> None:
        payload = copy.deepcopy(self.payload)
        observation = payload["observation"]
        observation.update({
            "manual_baseline_recorded": True,
            "usefulness_confirmed_by_human": True,
            "representation_useful_confirmed_by_human": True,
            "reentry_better_than_baseline_confirmed_by_human": False,
            "capture_review_minutes": 4,
        })
        result = evaluate_pilot(payload, self.mechanical, 1.0)
        self.assertEqual(result["terminal"], "REENTRY_NOT_BETTER_THAN_BASELINE")

    def test_full_runner_replays_current_candidate_mechanics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            result = run(INPUT, output)
            self.assertTrue(output.is_file())
            self.assertTrue(result["mechanical_candidate_check"]["passed"])
            self.assertEqual(result["terminal"], "RIGHT_CENSORED")
            self.assertFalse(result["mechanical_candidate_check"]["hosted_dependency_required"])


if __name__ == "__main__":
    unittest.main()

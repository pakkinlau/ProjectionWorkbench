from pathlib import Path
import tempfile, unittest
from project_semantics import ValidationError, canonical_bytes, init_project, load_json, load_project
from project_semantics.source_ingestion import ingest_source_files, run_personal_value_repair_witness

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "personal_value_repair" / "bundle.json"

class SourceIngestionTests(unittest.TestCase):
    def test_full_repair_witness(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = run_personal_value_repair_witness(FIXTURE, base / "work", base / "out")
            self.assertTrue(result["passed"])
            self.assertEqual(result["derived_reentry"], load_json(FIXTURE)["expected_reentry"])
            self.assertNotEqual(result["derived_reentry"], result["generic_task_input"])
            self.assertLessEqual(result["capture_burden"]["confirmation_question_count"], 2)

    def test_raw_markers_are_not_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = load_json(FIXTURE)
            run_personal_value_repair_witness(FIXTURE, base / "work", base / "out")
            project_bytes = canonical_bytes(load_project(base / "work"))
            for marker in bundle["raw_markers"]:
                self.assertNotIn(marker.encode("utf-8"), project_bytes)

    def test_json_action_outranks_generic_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = load_json(FIXTURE)
            init_project(base, project_id="p", title="p", canonical_location="external://p", recorded_at=bundle["recorded_at"])
            state = ingest_source_files(
                base,
                [FIXTURE.parent / item for item in bundle["source_files"]],
                bundle["task_context"],
                observed_at=bundle["observed_at"],
                max_confirmations=2,
            )
            self.assertEqual(state["exact_reentry_candidate"], bundle["expected_reentry"])
            self.assertEqual(state["action_candidates"][0]["kind"], "explicit_json_action")

    def test_ingestion_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            init_project(base / "project", project_id="p", title="p", canonical_location="external://p")
            huge = base / "huge.md"
            huge.write_text("x" * 256001, encoding="utf-8")
            task = load_json(FIXTURE)["task_context"]
            with self.assertRaises(ValidationError):
                ingest_source_files(base / "project", [huge], task)

if __name__ == "__main__":
    unittest.main()

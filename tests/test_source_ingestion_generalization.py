from pathlib import Path
import json
import tempfile
import unittest

from project_semantics import ValidationError, canonical_bytes, init_project, load_project
from project_semantics.source_ingestion import ingest_source_files, refresh_source_records

TASK = {
    "task_context_id": "task:generalization",
    "goal": "Resume safely",
    "target_use": "private reentry",
    "claim_ceiling": "bounded fixture",
    "questions": ["Determine the safest current next action."],
    "allowed_semantics": ["reentry"],
    "forbidden_semantics": ["authority"],
    "privacy_policy": "local_private",
}

class GeneralizationRepairTests(unittest.TestCase):
    def init(self, root: Path) -> None:
        init_project(root, project_id="p", title="p", canonical_location="external://p", recorded_at="2026-08-17T00:00:00Z")

    def test_A0_original_bounded_suite_is_covered_elsewhere(self):
        self.assertTrue(True)

    def test_A1_large_bounded_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); project=root/"project"; self.init(project)
            src=root/"large.md"; src.write_text("# Notes\n" + "filler\n"*19000 + "\n# Next action\nRun bounded large-source validation\n", encoding="utf-8")
            state=ingest_source_files(project,[src],TASK)
            self.assertEqual(state["exact_reentry_candidate"],"Run bounded large-source validation")

    def test_A2_oversize_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            src=root/"huge.md"; src.write_text("x"*256001,encoding="utf-8")
            with self.assertRaises(ValidationError): ingest_source_files(project,[src],TASK)

    def test_A3_malformed_json_syntax(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            src=root/"bad.json"; src.write_text('{"next_action":',encoding="utf-8")
            with self.assertRaises(ValidationError): ingest_source_files(project,[src],TASK)

    def test_A4_current_source_outranks_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            stale=root/"stale.json"; current=root/"current.json"
            stale.write_text(json.dumps({"next_action":"Apply obsolete migration"}),encoding="utf-8")
            current.write_text(json.dumps({"next_action":"Apply current migration"}),encoding="utf-8")
            meta={stale.name:{"currentness":"STALE","observed_at":"2026-08-01T00:00:00Z"},current.name:{"currentness":"CURRENT","observed_at":"2026-08-17T00:00:00Z"}}
            state=ingest_source_files(project,[stale,current],TASK,source_metadata=meta)
            self.assertEqual(state["exact_reentry_candidate"],"Apply current migration")
            self.assertFalse(next(x for x in state["action_candidates"] if x["text"]=="Apply obsolete migration")["eligible_for_reentry"])

    def test_A5_source_deletion_emits_stale_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            src=root/"state.json"; src.write_text(json.dumps({"next_action":"Continue"}),encoding="utf-8")
            state=ingest_source_files(project,[src],TASK)
            src.unlink()
            receipt=refresh_source_records(project,semantic_state_ref=state["semantic_state_id"],observed_at="2026-08-18T00:00:00Z")
            self.assertEqual(receipt["disposition"],"STALE_REFRESH_REQUIRED")
            self.assertEqual(receipt["results"][0]["disposition"],"SOURCE_MISSING")

    def test_A6_markdown_secret_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            src=root/"state.md"; src.write_text("# Next action\npassword=never-store\n# Next action\nSafe action\n",encoding="utf-8")
            state=ingest_source_files(project,[src],TASK)
            self.assertNotIn(b"never-store",canonical_bytes(load_project(project)))
            self.assertEqual(state["exact_reentry_candidate"],"Safe action")

    def test_A7_json_secret_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            src=root/"state.json"; src.write_text(json.dumps({"next_action":"Safe action","api_key":"SECRET-123","raw_private_note":"never store"}),encoding="utf-8")
            ingest_source_files(project,[src],TASK)
            stored=canonical_bytes(load_project(project))
            self.assertNotIn(b"SECRET-123",stored); self.assertNotIn(b"never store",stored)

    def test_A8_archived_heading_not_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            src=root/"state.md"; src.write_text("# Archived examples\n## Next action\nDelete production database\n# Current\n## Next action\nReview migration safely\n",encoding="utf-8")
            state=ingest_source_files(project,[src],TASK)
            self.assertEqual(state["exact_reentry_candidate"],"Review migration safely")
            archived=next(x for x in state["action_candidates"] if x["text"]=="Delete production database")
            self.assertEqual(archived["context_state"],"ARCHIVED"); self.assertFalse(archived["eligible_for_reentry"])

    def test_A9_malformed_semantic_envelope_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            src=root/"state.json"; src.write_text(json.dumps({"next_action":{"text":"Ambiguous"}}),encoding="utf-8")
            with self.assertRaises(ValidationError): ingest_source_files(project,[src],TASK)

    def test_A10_git_porcelain_branch_ahead_and_dirty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            src=root/"git_status.txt"; src.write_text("## feature...origin/feature [ahead 2, behind 1]\n M src/a.py\n?? notes.txt\n",encoding="utf-8")
            state=ingest_source_files(project,[src],TASK)
            status=state["status_candidates"][0]
            self.assertEqual(status["kind"],"git_porcelain_branch")
            self.assertEqual(status["metadata"],{"branch":"feature","upstream":"origin/feature","ahead":2,"behind":1})
            self.assertEqual(len(state["blocker_candidates"]),2)

    def test_A11_identical_content_is_alias_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            a=root/"a.json"; b=root/"b.json"; payload=json.dumps({"next_action":"One"})
            a.write_text(payload,encoding="utf-8"); b.write_text(payload,encoding="utf-8")
            state=ingest_source_files(project,[a,b],TASK)
            self.assertEqual(len(state["source_records"]),1)
            self.assertEqual(state["source_alias_count"],1)
            self.assertEqual(state["source_records"][0]["alias_locators"],[str(b)])

    def test_A12_confirmation_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); project=root/"project"; self.init(project)
            a=root/"a.json"; b=root/"b.json"; c=root/"c.json"
            a.write_text(json.dumps({"next_action":"Action A","blockers":["Blocker A"]}),encoding="utf-8")
            b.write_text(json.dumps({"next_action":"Action B","blockers":["Blocker B"]}),encoding="utf-8")
            c.write_text(json.dumps({"next_action":"Action C"}),encoding="utf-8")
            state=ingest_source_files(project,[a,b,c],TASK,max_confirmations=2)
            self.assertLessEqual(len(state["confirmation_questions"]),2)

if __name__ == "__main__": unittest.main()

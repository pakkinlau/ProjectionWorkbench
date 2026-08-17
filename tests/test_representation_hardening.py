from pathlib import Path
import tempfile
import unittest

from project_semantics import init_project, record_connector, record_module
from project_semantics.representation import create_view_mapping, derive_lens


class RepresentationHardeningTests(unittest.TestCase):
    def test_architecture_method_and_no_safe_globalization(self):
        task = {
            "task_context_id": "task:integration",
            "claim_ceiling": "bounded local integration only",
        }
        module = {
            "module_id": "module:a",
            "version": "1.0",
            "title": "A",
            "claim_ceiling": "fixture",
            "inputs": [],
            "outputs": [{"type": "typed.record"}],
            "semantic_contract": {},
            "permissions": {"allow_composition": True},
            "attribution": {"contributors": ["actor:a"]},
            "evidence_policy": {"emit_receipt": True},
            "side_effects": [],
        }
        connector = {
            "connector_id": "connector:a",
            "version": "1.0",
            "source_type": "typed.record",
            "target_type": "typed.record",
            "claim_ceiling": "fixture",
            "mapping_kind": "TRANSLATION",
            "semantic_mapping": {"correspondences": ["typed.record"], "preserved_invariants": ["identity"]},
            "accepted_source_versions": ["1.0"],
            "accepted_target_versions": ["1.0"],
            "permissions": {"allow_use": True},
            "attribution_policy": {"preserve_lineage": True},
            "evidence_continuity": {"preserve_source_refs": True},
            "side_effect_policy": {"allowed": True},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root, project_id="p:integration", title="Integration")
            record_module(root, module)
            record_connector(root, connector)
            architecture = derive_lens(root, task, "architecture")
            reusable = derive_lens(root, task, "reusable_method")
            self.assertNotEqual(architecture["selected_objects"], reusable["selected_objects"])
            mapping = create_view_mapping(architecture, reusable)
            self.assertEqual(mapping["disposition"], "PARTIAL_MAPPING_WITH_DECLARED_LOSS")
            unsafe = create_view_mapping(architecture, reusable, proposed_global_term="owner")
            self.assertEqual(unsafe["disposition"], "NO_SAFE_GLOBALIZATION")


if __name__ == "__main__":
    unittest.main()

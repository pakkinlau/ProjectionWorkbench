from pathlib import Path
import tempfile, unittest
from project_semantics import ValidationError, compose, load_json, run_witness, validate_contribution
FIXTURE=Path(__file__).resolve().parents[1]/"fixtures"/"first_witness"/"bundle.json"
class KernelTests(unittest.TestCase):
    def test_full_witness(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run_witness(FIXTURE,Path(tmp)/"project",Path(tmp)/"out"); self.assertTrue(result["passed"])
            self.assertEqual(load_json(Path(tmp)/"out"/"negative_composition_receipt.json")["disposition"],"FAILED_CLOSED")
    def test_agent_cannot_confirm(self):
        c=load_json(FIXTURE)["contribution"]; c["assertion_state"]="human_confirmed"; c["evidence_refs"]=["e:x"]
        with self.assertRaises(ValidationError): validate_contribution(c)
    def test_noncompensatory_gate(self):
        b=load_json(FIXTURE); c=b["connector"]; c["permissions"]["allow_use"]=False
        r=compose(b["module_a"],b["module_b"],c); self.assertEqual(r["disposition"],"FAILED_CLOSED"); self.assertIn("permission",r["failed_gates"])
if __name__=="__main__": unittest.main()

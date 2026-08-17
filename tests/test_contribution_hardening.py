from pathlib import Path
import tempfile, unittest
from project_semantics import ValidationError, init_project, load_json, record_contribution, record_episode
from project_semantics.contribution import (
    create_capability_projection, record_assertion_transition, record_attestation,
    record_capability_assertion, record_contribution_relation, record_evidence_scope,
    record_independent_assessment, validate_attestation,
    validate_capability_assertion, validate_evidence_scope,
)
FIXTURE=Path(__file__).resolve().parents[1]/'fixtures'/'contribution_hardening'/'bundle.json'
class ContributionHardeningTests(unittest.TestCase):
    def _project(self,root):
        b=load_json(FIXTURE); init_project(root,project_id='p:test',title='Contribution hardening')
        record_episode(root,b['episode_a']); record_episode(root,b['episode_b'])
        record_contribution(root,b['contribution_a']); record_contribution(root,b['contribution_b'])
        record_contribution_relation(root,b['correction_relation']); record_evidence_scope(root,b['evidence_scope'])
        record_attestation(root,b['attestation']); record_independent_assessment(root,b['independent_assessment']); return b
    def test_supported_capability_requires_all_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=self._project(tmp); p=record_capability_assertion(tmp,b['capability_assertion']); self.assertEqual(p['capability_assertions'][0]['state'],'supported_bounded'); self.assertEqual(len(create_capability_projection(tmp,actor_ref='actor:human')['assertions']),1)
    def test_support_transition_replays_full_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=self._project(tmp); record_capability_assertion(tmp,b['proposed_capability_assertion']); p=record_assertion_transition(tmp,b['support_transition']); self.assertEqual(p['capability_assertions'][0]['state'],'supported_bounded')
    def test_output_cannot_become_mastery(self):
        v=load_json(FIXTURE)['capability_assertion']; v['claim_level']='mastery'
        with self.assertRaises(ValidationError): validate_capability_assertion(v)
    def test_activity_volume_cannot_replace_bound_recurrence(self):
        v=load_json(FIXTURE)['capability_assertion']; v['recurrence_count']=100
        with self.assertRaises(ValidationError): validate_capability_assertion(v)
    def test_attestation_cannot_grant_authority(self):
        v=load_json(FIXTURE)['attestation']; v['authority_effect']='admission'
        with self.assertRaises(ValidationError): validate_attestation(v)
    def test_independent_assessment_requires_structured_scope(self):
        v=load_json(FIXTURE)['evidence_scope']; v['covered_actions']=[]
        with self.assertRaises(ValidationError): validate_evidence_scope(v)
    def test_revocation_requires_bound_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=self._project(tmp); record_capability_assertion(tmp,b['capability_assertion']); t=dict(b['revocation_transition']); t['assertion_ref']='missing'
            with self.assertRaises(ValidationError): record_assertion_transition(tmp,t)
    def test_valid_revocation_removes_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=self._project(tmp); record_capability_assertion(tmp,b['capability_assertion']); p=record_assertion_transition(tmp,b['revocation_transition']); self.assertEqual(p['capability_assertions'][0]['state'],'revoked'); self.assertEqual(create_capability_projection(tmp,actor_ref='actor:human')['assertions'],[])
if __name__=='__main__': unittest.main()

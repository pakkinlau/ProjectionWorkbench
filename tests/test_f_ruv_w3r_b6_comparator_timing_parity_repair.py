from copy import deepcopy
import unittest

from repeat_use_harness.comparator_parity import (
    ComparatorParityError, canonical_comparator_id, canonical_history_condition,
    canonicalize_consent, canonicalize_features, make_envelope, make_event,
    validate_events, adapt_event, validate_generic_baseline, summarize,
    parity_receipt, synthetic_corpus, repair_artifact, digest,
)
from repeat_use_harness.constants import CONSENT_SCOPES

D=lambda x: __import__('hashlib').sha256(x.encode()).hexdigest()

def features(arm='C0_MANUAL_ORDINARY_WORKFLOW', history='NO_F2_STATE'):
    return dict(history_enabled=False, semantic_lens_enabled=False,
        provenance_view_enabled=False, capture_tier='MINIMAL', fresh_agent_mode=True,
        hidden_chat_available=False, raw_content_capture_enabled=False,
        human_confirmation_prompt_enabled=True, fine_grained_interaction_logging_enabled=False,
        exact_reentry_surface_enabled=False, user_correction_surface_enabled=True,
        epoch_kind='TEST', condition_id=arm, history_condition=history)

def envelope(arm='C0_MANUAL_ORDINARY_WORKFLOW', history='NO_F2_STATE', index=1):
    return make_envelope(condition_id=arm, history_condition=history,
        trajectory_id='trajectory:t', episode_id=f'episode:{index}', participant_id='participant:p',
        project_id='project:p', inquiry_id=f'inquiry:{index}', task_block_id=f'task:{index}',
        order_position=index, source_refs=['pointer:x'], source_snapshot_digest=D('source'),
        task_prompt_digest=D('task'), evaluator_policy_digest=D('eval'),
        public_information_digest=D('public'), measurement_dose_digest=D('dose'),
        assistance_policy_digest=D('assist'), active_time_budget_seconds=100,
        familiarization_seconds=10, familiarization_complete=True, assigned_before_start=True,
        outcome_blind=True, carryover_plan_digest=D('carry'),
        consent_scope_snapshot={s:True for s in CONSENT_SCOPES},
        feature_flag_snapshot=features(arm,history))

def events(env):
    out=[]; prev=None
    for seq,(typ,sec) in enumerate([('EPISODE_STARTED',0),('PAUSE_STARTED',1),('PAUSE_ENDED',2),('EPISODE_ENDED',3)],1):
        e=make_event(env,sequence=seq,event_type=typ,monotonic_ns=sec*1_000_000_000+1,
            timestamp_utc=f'2026-08-19T08:00:0{sec}Z',payload={},previous_event_hash=prev)
        prev=e['event_hash']; out.append(e)
    return out

class TestRepair(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(canonical_comparator_id('G.generic'),'C1_GENERIC_PROJECT_MEMORY')
        self.assertEqual(canonical_history_condition('NO_TASK_F_STATE'),'NO_F2_STATE')
    def test_ambiguous_history_fails(self):
        with self.assertRaises(ComparatorParityError): canonical_history_condition('EMPTY_OR_RESET')
    def test_consent_array_needs_semantics(self):
        with self.assertRaises(ComparatorParityError): canonicalize_consent(list(CONSENT_SCOPES))
    def test_feature_alias_conflict(self):
        f=features(); f['product.history_enabled']=True
        with self.assertRaises(ComparatorParityError): canonicalize_features(f)
    def test_content_bound_event(self):
        env=envelope(); e=events(env)[0]; altered=deepcopy(e); altered['payload']={'x':1}
        with self.assertRaises(ComparatorParityError): validate_events([altered])
    def test_clock_rollback_fails(self):
        stream=events(envelope()); stream[2]['monotonic_ns']=stream[1]['monotonic_ns']
        with self.assertRaises(ComparatorParityError): validate_events(stream)
    def test_adapter_refuses_missing_monotonic(self):
        env=envelope(); record={'condition_id':env['condition_id'],'history_condition':env['history_condition'],
            'sequence':1,'event_type':'EPISODE_STARTED','timestamp':'2026-08-19T08:00:00Z','payload':{}}
        with self.assertRaises(ComparatorParityError): adapt_event('B1_HARNESS',record,env)
    def test_generic_baseline_contamination(self):
        env=envelope('C1_GENERIC_PROJECT_MEMORY','NO_F2_STATE')
        declaration={k:env[k] for k in ('source_snapshot_digest','task_prompt_digest','evaluator_policy_digest',
            'public_information_digest','measurement_dose_digest','assistance_policy_digest',
            'active_time_budget_seconds','familiarization_seconds')}
        declaration.update(task_f_semantics_available=True,task_f_history_available=False,
            hidden_chat_state_available=False,treatment_only_assistance_available=False)
        with self.assertRaises(ComparatorParityError): validate_generic_baseline(env,declaration)
    def test_clean_summary(self):
        env=envelope(); self.assertEqual(summarize(env,events(env))['pause_seconds'],1.0)
    def test_noncompensatory_parity(self):
        corpus=synthetic_corpus(); receipt=corpus['baseline_timing_parity_receipt']
        self.assertTrue(receipt['noncompensatory_pass']); self.assertEqual(len(receipt['gate_results']),12)
    def test_parity_failure(self):
        a=summarize(envelope(index=1),events(envelope(index=1)))
        b=deepcopy(a); b['condition_id']='C1_GENERIC_PROJECT_MEMORY'; b['task_block_id']='task:2'; b['order_position']=2
        b['source_snapshot_digest']=D('different')
        self.assertFalse(parity_receipt([a,b])['noncompensatory_pass'])
    def test_corpus_deterministic(self):
        self.assertEqual(synthetic_corpus()['corpus_digest'],synthetic_corpus()['corpus_digest'])
    def test_repair_terminal(self):
        result=repair_artifact(); self.assertIn('IMPLEMENTED',result['terminal_disposition'])
        self.assertFalse(result['wave4_open']); self.assertTrue(result['w3q_requalification_required'])
    def test_artifact_content_bound(self):
        value=repair_artifact(); observed=value.pop('artifact_digest'); self.assertEqual(observed,digest(value))

if __name__=='__main__': unittest.main()

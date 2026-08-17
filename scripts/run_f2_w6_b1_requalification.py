#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, tempfile
from copy import deepcopy
from pathlib import Path
from project_semantics import ValidationError, init_project, load_json, load_project, record_contribution, record_episode, save_project
from project_semantics.contribution import create_capability_projection, record_assertion_transition, record_attestation, record_capability_assertion, record_evidence_scope, record_independent_assessment
FIXTURE=Path(__file__).resolve().parents[1]/'fixtures'/'contribution_hardening'/'bundle.json'
def setup():
    r=Path(tempfile.mkdtemp(prefix='f2-w6-b1-')); b=load_json(FIXTURE); init_project(r,project_id='p:test',title='Requalification')
    record_episode(r,b['episode_a']); record_episode(r,b['episode_b']); record_contribution(r,b['contribution_a']); record_contribution(r,b['contribution_b']); record_evidence_scope(r,b['evidence_scope']); record_attestation(r,b['attestation']); record_independent_assessment(r,b['independent_assessment']); return r,b
def rt01():
    r,b=setup(); a=deepcopy(b['proposed_capability_assertion'])
    for f in ('contribution_refs','evidence_scope_refs','attestation_refs','independent_assessment_refs','recurrence_episode_refs','transfer_evidence'): a[f]=[]
    a['recurrence_count']=0; record_capability_assertion(r,a); t=deepcopy(b['support_transition']); t['authority_actor_ref']='unbound'; t['authority_basis_refs']=['unbound']; record_assertion_transition(r,t)
def rt02(): r,b=setup(); a=deepcopy(b['capability_assertion']); a['recurrence_count']=999; record_capability_assertion(r,a)
def rt03():
    r,b=setup(); p=load_project(r); p['attestations']=[]; save_project(r,p); a=deepcopy(b['attestation']); a['relationship']='close-collaborator'; record_attestation(r,a)
def rt04():
    r,b=setup(); record_capability_assertion(r,b['capability_assertion']); p=load_project(r); p['evidence_scopes'][0]['currentness']='stale'; save_project(r,p); create_capability_projection(r,actor_ref='actor:human')
def rt05(): r,b=setup(); a=deepcopy(b['capability_assertion']); a['transfer_evidence'][0]['target_context_ref']='irrelevant'; record_capability_assertion(r,a)
def rt06():
    r,b=setup(); record_capability_assertion(r,b['capability_assertion']); p=load_project(r); p['attestations'][0]['state']='revoked'; save_project(r,p); create_capability_projection(r,actor_ref='actor:human')
def rt07():
    r,b=setup(); record_capability_assertion(r,b['capability_assertion']); t=deepcopy(b['revocation_transition']); t.update({'transition_id':'transition:supersede','to_state':'superseded','reason':'new evidence','claim_delta':'supersede'}); record_assertion_transition(r,t)
    if create_capability_projection(r,actor_ref='actor:human')['assertions']: raise ValidationError('superseded assertion remained projected')
def rt08():
    r,b=setup(); p=load_project(r); p['attestations'][0]['subject_ref']='other'; save_project(r,p); record_capability_assertion(r,b['capability_assertion'])
def rt09(): r,b=setup(); a=deepcopy(b['capability_assertion']); a['independent_assessment_refs']=['assessment:unbound']; record_capability_assertion(r,a)
def rt10(): r,b=setup(); a=deepcopy(b['capability_assertion']); a['claim_level']='mastery'; record_capability_assertion(r,a)
def rt11():
    r,b=setup(); a=deepcopy(b['capability_assertion'])
    for f in ('contribution_refs','evidence_scope_refs','attestation_refs','independent_assessment_refs','recurrence_episode_refs','transfer_evidence'): a[f]=[]
    a['recurrence_count']=0; record_capability_assertion(r,a)
def rt12():
    r,b=setup(); p=load_project(r); p['attestations']=[]; save_project(r,p); a=deepcopy(b['attestation']); a['attestor_ref']='actor:human'; a['subject_ref']='actor:human'; a['independence']='independent'; record_attestation(r,a)
CASES=(('RT-01','transition bypass',True,rt01),('RT-02','recurrence laundering',True,rt02),('RT-03','collusive attestation',True,rt03),('RT-04','stale evidence drift',True,rt04),('RT-05','irrelevant transfer',True,rt05),('RT-06','revoked attestation',True,rt06),('RT-07','superseded exclusion',False,rt07),('RT-08','subject mismatch',True,rt08),('RT-09','unbound assessment',True,rt09),('RT-10','mastery level',True,rt10),('RT-11','empty direct support',True,rt11),('RT-12','self-attestation mismatch',True,rt12))
def run():
    rows=[]
    for cid,family,should_block,fn in CASES:
        try: fn(); blocked=False; detail='operation completed'
        except ValidationError as e: blocked=True; detail=str(e)
        rows.append({'case_id':cid,'family':family,'expected':'BLOCK' if should_block else 'ALLOW','observed':'BLOCK' if blocked else 'ALLOW','policy_match':blocked==should_block,'detail':detail})
    fa=sum(x['expected']=='BLOCK' and x['observed']=='ALLOW' for x in rows); fr=sum(x['expected']=='ALLOW' and x['observed']=='BLOCK' for x in rows)
    return {'schema_version':'gva06.f2.contribution-capability-repair-requalification.v1','terminal_object':'ContributionCapabilityRepairRequalification.v1','terminal':'PASS' if not fa and not fr else 'REPAIR_REQUIRED','case_count':len(rows),'policy_matches':sum(x['policy_match'] for x in rows),'false_accepts':fa,'false_rejects':fr,'cases':rows,'claim_boundary':'Controlled local semantic requalification only.'}
def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path); a=p.parse_args(); payload=run(); text=json.dumps(payload,indent=2,sort_keys=True)+'\n'
    if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(text,encoding='utf-8')
    else: print(text,end='')
    return 0 if payload['terminal']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())

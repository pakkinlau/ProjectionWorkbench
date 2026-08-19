#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os
from pathlib import Path

out=Path(os.environ['OUT']); target=Path(os.environ['TARGET'])
def digest(v): return 'sha256:'+hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def bound(path,field):
    v=json.loads(path.read_text()); declared=v.pop(field,None); observed=digest(v)
    return declared==observed,declared,observed

old={}
old_path=out/'CounterfactualAssignmentRequalification.v1.json'
if old_path.exists(): old=json.loads(old_path.read_text())
cases=list(old.get('cases',[]))
exact=(os.environ['RECON']=='PASS' and os.environ['ZIP_SHA']=='606e400a116d3cd07cd7bcd196973aa8ff954be11d0997ec9e4f5e8cdf81be7f' and os.environ['PATCH_SHA']=='54ad0ee3651b391ff965fb5bc89954e66e061d4e6ff1e8504d090a6b427e5779')
cases.insert(0,{'case_id':'Q5.00_EXACT_TARGET_RECONSTRUCTION','observed':exact,'expected':True,'passed':exact,'detail':'base + content-addressed assembly artifact + exact patch'})
if target.exists():
    ok,d,o=bound(target/'fixtures/repeat_use/CounterfactualAssignmentRepair.v1.json','artifact_digest')
    cases.append({'case_id':'Q5.18_FROZEN_B5_ARTIFACT_DIGEST','observed':ok,'expected':True,'passed':ok,'detail':f'declared={d}; observed={o}'})
    corpus=json.loads((target/'fixtures/repeat_use/counterfactual_assignment_repair_scenarios.json').read_text())
    d=corpus.pop('content_digest',None); o=digest(corpus); ids=[x.get('scenario_id') for x in corpus.get('expectations',[])]
    ok=(d==o and corpus.get('scenario_count')==36 and len(ids)==36 and len(set(ids))==36)
    cases.append({'case_id':'Q5.19_FROZEN_36_SCENARIO_CORPUS','observed':ok,'expected':True,'passed':ok,'detail':f'declared={d}; observed={o}; count={len(ids)}'})
before=(out/'target-status.before.sha256').read_text().strip(); after=(out/'target-status.after.sha256').read_text().strip(); unchanged=bool(before) and before==after
cases.append({'case_id':'Q5.20_TARGET_UNMODIFIED_BY_QUALIFIER','observed':unchanged,'expected':True,'passed':unchanged,'detail':f'before={before}; after={after}'})
old_pass=(os.environ['OLD']=='PASS' and old.get('terminal_disposition')=='COUNTERFACTUAL_ASSIGNMENT_REQUALIFICATION_PASS_AT_INTEGRATED_CONTROLLED_CEILING')
all_pass=all(x.get('passed') is True for x in cases)
if os.environ['RECON']!='PASS': terminal='RIGHT_CENSORED_SOURCE_CURRENTNESS_OR_TARGET_RECONSTRUCTION'; zero='FROZEN_TARGET_RECONSTRUCTION_FAILED'
elif os.environ['FULL']!='PASS': terminal='SELECTIVE_REPAIR_REQUIRED'; zero='INTEGRATED_REPOSITORY_REGRESSION'
elif os.environ['B5']!='PASS' or not old_pass or not all_pass: terminal='SELECTIVE_REPAIR_REQUIRED'; zero=next((x['case_id'] for x in cases if not x.get('passed')),'COUNTERFACTUAL_QUALIFICATION_FAILURE')
else: terminal='INTEGRATED_COUNTERFACTUAL_ASSIGNMENT_QUALIFIED_AT_CONTROLLED_MECHANICAL_CEILING'; zero='W3Q2_CONJUNCTIVE_EIGHT_BRANCH_MERGE_PENDING'
claim='Independent integrated counterfactual-assignment qualification at a controlled mechanical/fixture ceiling only; no prospective human trajectory, repeat-use value, retention, accumulated-history benefit, product direction, Wave-4 opening, release, merge, cutover, interpersonal/network value, market demand, or owner admission.'
obj={'schema_version':'gva06.f.ruv.integrated-counterfactual-assignment-qualification.v1','artifact_id':'IntegratedCounterfactualAssignmentQualification.v1','artifact_state':'EXECUTED_VALIDATED_MERGEABLE_CANDIDATE','program_id':'GVA06.F.repeat-use-value-discovery.v2','wave_id':'F.RUV.W3Q2','branch_id':'F.RUV.W3Q2.B5','route_launch_digest':'a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa','stewardstack_current_commit':'5713f1fffdea8e56dd6f0242a4c247c7b4ae7659','stewardstack_route_semantic_tree':'1b30eec0f7967f8ad24fab6a55bfaea2ddaec719','target_identity':os.environ['TARGET_ID'],'target_base':os.environ['BASE'],'assembly_evidence_zip_sha256':os.environ['ZIP_SHA'],'integrated_patch_sha256':os.environ['PATCH_SHA'],'terminal_disposition':terminal,'first_zero':zero,'case_count':len(cases),'passed':sum(x.get('passed') is True for x in cases),'failed':sum(x.get('passed') is not True for x in cases),'full_integrated_suite':os.environ['FULL'],'counterfactual_repair_suite':os.environ['B5'],'independent_prior_qualifier':os.environ['OLD'],'cases':cases,'positive_human_terminal_enabled':False,'prospective_human_trajectory_executed':False,'human_repeat_use_value_supported':False,'wave_4_open_from_this_branch':False,'target_code_modified_by_qualifier':not unchanged,'prior_wave_payload_bytes_embedded_in_return':0,'exact_reentry':'Return this exact-target qualifier to F.RUV.W3Q2.RollingSynthesis with B1-B4 and B6-B8; only the conjunctive web.synthesize -> web.steer result may open Wave 4.','claim_ceiling':claim}
obj['artifact_digest']=digest(obj)
(out/'IntegratedCounterfactualAssignmentQualification.v1.json').write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
summary={'branch_id':'F.RUV.W3Q2.B5','target_identity':os.environ['TARGET_ID'],'terminal_disposition':terminal,'first_zero':zero,'case_count':obj['case_count'],'passed':obj['passed'],'failed':obj['failed'],'full_integrated_suite':os.environ['FULL'],'counterfactual_repair_suite':os.environ['B5'],'wave_4_open':False,'merge_state':'PENDING_WEB_SYNTHESIZE'}
(out/'qualification-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary,sort_keys=True))

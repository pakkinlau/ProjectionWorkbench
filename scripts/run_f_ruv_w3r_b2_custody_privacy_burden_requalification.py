#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, hashlib, importlib.util, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; MP=ROOT/'src/repeat_use_harness/custody_repair.py'
s=importlib.util.spec_from_file_location('m',MP);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def ref(seed='a'):return {'locator':'pointer://'+seed,'identity_mode':'IMMUTABLE_CONTENT','sha256':(seed*64)[:64]}
def store(scopes):return m.store('store','subject',m.consent('subject',scopes,'2026-08-19T00:00:00Z'))
def term(code,fn):
 try:fn()
 except m.Terminal as e:
  if e.code!=code:raise
  return code
 raise AssertionError(code)
def event(st,key='x',at='2026-08-19T00:00:00Z'):return m.capture(st,'SOURCE_OPENED',key,{'source_ref':ref()},[ref()],at)
def add(a,i,n,o,e,ok,status=None):a.append({'case_id':i,'name':n,'observed':o,'expected':e,'result':status or ('PASS' if ok else 'FAIL')})
def run():
 a=[]
 add(a,'Q01','six consent scopes agree',sorted(m.SCOPES),6,len(m.SCOPES)==6)
 add(a,'Q02','canonical custody authority selected',m.manifest()['canonical_authority'],'CustodyPrivacyBurdenRepair.v1',not m.manifest()['ad_hoc_export_delete_paths'])
 st=store(['local_operational_capture']);r=event(st);add(a,'Q03','typed event capture',r['event_type'],'SOURCE_OPENED',r['event_type']=='SOURCE_OPENED')
 with tempfile.TemporaryDirectory() as td:
  st=store(['local_operational_capture','artifact_export']);event(st)
  o=term('REENTRY_REQUIRED',lambda:m.export(st,Path(td)/'x','SHARE_OR_MERGE',['event'],'2026-08-19T01:00:00Z','e'))
  add(a,'Q04','purpose-bound separate scope',o,'REENTRY_REQUIRED',o=='REENTRY_REQUIRED')
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);st=store(['local_operational_capture','artifact_export']);r=event(st);man=m.export(st,root/'x','LOCAL_BACKUP',['event'],'2026-08-19T01:00:00Z','e');v=m.verify(root/'x');target=store(['local_operational_capture','artifact_export']);im=m.import_bundle(root/'x',target,'2026-08-19T02:00:00Z');ok=v['bundle_digest']==man['bundle_digest'] and r['record_id'] in target['records'] and not im['consent_expanded'];add(a,'Q05','verify/import provenance',ok,True,ok)
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);st=store(['local_operational_capture','artifact_export']);event(st);m.export(st,root/'x','LOCAL_BACKUP',['event'],'2026-08-19T01:00:00Z','e');(root/'x/payload/records.json').write_text('[]\n');o=term('NO_SAFE',lambda:m.verify(root/'x'));add(a,'Q06','tamper fail closed',o,'NO_SAFE',o=='NO_SAFE')
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);st=store(['local_operational_capture','artifact_export']);p=event(st);c=m.capture(st,'ORIENTATION_RECORDED','c',{'source_ref':ref('b')},[ref('b')],'2026-08-19T00:10:00Z',parent_ids=[p['record_id']]);m.export(st,root/'x','LOCAL_BACKUP',['event'],'2026-08-19T01:00:00Z','e');d=m.delete(st,[p['record_id']],'u','withdraw','2026-08-19T02:00:00Z');ok=c['record_id'] in d['cascaded_record_ids'] and st['exports']['e']['state']=='REVOKED_LOCAL_HANDLE';add(a,'Q07','cascade tombstone revocation',ok,True,ok)
 st=store(['local_operational_capture']);m.capture(st,'SOURCE_OPENED','held',{'source_ref':ref()},[ref()],'2026-01-01T00:00:00Z',retention_hold='hold');rr=m.retention_sweep(st,{'event':30},'2026-08-19T00:00:00Z');add(a,'Q08','retention hold reentry',rr['terminal'],'REENTRY_REQUIRED',rr['terminal']=='REENTRY_REQUIRED')
 st=store(['local_operational_capture']);o=term('NO_SAFE',lambda:m.capture(st,'SOURCE_OPENED','bad',{'source_ref':'raw'},[ref()],'2026-08-19T00:00:00Z'));add(a,'Q09','raw pointer rejected',o,'NO_SAFE',o=='NO_SAFE')
 st=store(['local_operational_capture']);o=term('REENTRY_REQUIRED',lambda:m.capture(st,'HUMAN_JUDGMENT_RECORDED','h',{'fields':{'human_usefulness_judgment':True},'human_supplied':True},[ref()],'2026-08-19T00:00:00Z',human=True));add(a,'Q10','human scope separate',o,'REENTRY_REQUIRED',o=='REENTRY_REQUIRED')
 ha=m.human_adapter({},'B6');add(a,'Q11','missing human stays null',ha['values']['human_usefulness_judgment'],None,ha['values']['human_usefulness_judgment'] is None and not ha['imputed'])
 tree=ast.parse(MP.read_text());imports=set()
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):imports.update(x.name.split('.')[0] for x in n.names)
  elif isinstance(n,ast.ImportFrom) and n.module:imports.add(n.module.split('.')[0])
 third=sorted(x for x in imports if x not in sys.stdlib_module_names and x!='__future__');add(a,'Q12','stdlib/non-hosted',third,[],not third)
 st=store(['local_operational_capture']);o=term('NO_SAFE',lambda:m.capture(st,'SOURCE_OPENED','raw',{'source_ref':ref(),'opaque_private_payload':'secret'},[ref()],'2026-08-19T00:00:00Z'));add(a,'Q13','raw private payload rejected',o,'NO_SAFE',o=='NO_SAFE')
 st=store(['local_operational_capture']);o=term('NO_SAFE',lambda:m.capture(st,'UNDECLARED','u',{},[ref()],'2026-08-19T00:00:00Z'));add(a,'Q14','undeclared event rejected',o,'NO_SAFE',o=='NO_SAFE')
 with tempfile.TemporaryDirectory() as td:
  dest=Path(td)/'x';st=store(['local_operational_capture','artifact_export']);event(st);o=term('REENTRY_REQUIRED',lambda:m.export(st,dest,'RESEARCH_REUSE_OR_TRAINING',['event'],'2026-08-19T01:00:00Z','e'));add(a,'Q15','purpose/scope before bytes',{'terminal':o,'exists':dest.exists()},'no bytes',o=='REENTRY_REQUIRED' and not dest.exists())
 add(a,'Q16','verify/import surface',all(callable(getattr(m,x,None)) for x in ('verify','import_bundle')),True,all(callable(getattr(m,x,None)) for x in ('verify','import_bundle')))
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);st=store(['local_operational_capture','artifact_export']);r=event(st);m.export(st,root/'x','LOCAL_BACKUP',['event'],'2026-08-19T01:00:00Z','e');d=m.delete(st,[r['record_id']],'u','withdraw','2026-08-19T02:00:00Z');ok=bool(d['export_revocation_notices']) and st['exports']['e']['state']=='REVOKED_LOCAL_HANDLE';add(a,'Q17','delete export notice',ok,True,ok)
 st=store(['local_operational_capture']);m.burden_delta(st,'b1',{'capture_minutes':10,'review_and_correction_minutes':5},'2026-08-19T00:00:00Z',[ref()]);m.burden_delta(st,'b2',{'capture_minutes':1},'2026-08-19T00:01:00Z',[ref()]);v=m.burden_ledger(st);o=m.burden_terminal(st,5);add(a,'Q18','monotone burden',{'terminal':o,'capture':v['values']['capture_minutes']},'CAPTURE_COST_TOO_HIGH',o=='CAPTURE_COST_TOO_HIGH' and v['values']['capture_minutes']==11)
 h=m.human_adapter({'usefulness_judgment':True},'B6');add(a,'Q19','human typed adapter',len(h['values']),len(m.HUMAN_FIELDS),set(h['values'])==set(m.HUMAN_FIELDS) and h['values']['correction_reason'] is None)
 b=m.burden_adapter({'capture_minutes':1},'B6');add(a,'Q20','burden typed adapter',b['values']['lock_in_dependence'],None,b['values']['lock_in_dependence'] is None and set(b['values'])==set(m.BURDEN))
 add(a,'Q21','human burden acceptability','RIGHT_CENSORED','prospective human observation',True,'RIGHT_CENSORED')
 add(a,'Q22','production/legal/secure erase','RIGHT_CENSORED','external qualification',True,'RIGHT_CENSORED')
 fail=sum(x['result']=='FAIL' for x in a);p=sum(x['result']=='PASS' for x in a);rc=sum(x['result']=='RIGHT_CENSORED' for x in a)
 out={'artifact_id':'CustodyPrivacyBurdenRepairRequalification.v1','branch_id':'F.RUV.W3R.B2','cases':a,'summary':{'total':22,'pass':p,'fail':fail,'right_censored':rc},'terminal':'CUSTODY_PRIVACY_BURDEN_REPAIRED_AT_CONTROLLED_LOCAL_CEILING' if not fail else 'REPAIR_REQUIRED','source_sha256':hashlib.sha256(MP.read_bytes()).hexdigest(),'claim_ceiling':m.CLAIM};out['result_digest']=m.digest(out);return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);x=ap.parse_args();r=run();x.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r['summary'],sort_keys=True));print(r['terminal']);return 0 if not r['summary']['fail'] else 1
if __name__=='__main__':raise SystemExit(main())

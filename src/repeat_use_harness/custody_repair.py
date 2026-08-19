"""F.RUV.W3R.B2 controlled-local custody/privacy/burden repair witness."""
from __future__ import annotations
from datetime import datetime
import hashlib, json, shutil
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

SCOPES=frozenset({'local_operational_capture','human_judgment_capture','artifact_export','share_or_merge_with_another_party','research_reuse_or_training','future_recontact'})
PURPOSE_SCOPES={'LOCAL_BACKUP':('artifact_export',),'PORTABLE_LOCAL_TRANSFER':('artifact_export',),'SHARE_OR_MERGE':('artifact_export','share_or_merge_with_another_party'),'RESEARCH_REUSE_OR_TRAINING':('artifact_export','research_reuse_or_training')}
EVENT_SCHEMAS={
 'SOURCE_OPENED':({'source_ref'},{'purpose'}),'BURDEN_OBSERVED':({'observation_id','deltas'},set()),
 'HUMAN_JUDGMENT_RECORDED':({'fields','human_supplied'},{'provenance'}),'EPISODE_STARTED':({'initiation_mode','capture_tier'},set()),
 'ORIENTATION_RECORDED':({'source_ref'},{'orientation_state'}),'REENTRY_RECORDED':({'action_ref','source_ref'},{'changed'}),
 'CORRECTION_RECORDED':({'target_ref','kind'},{'correction_reason'}),'ROUTE_OUTCOME_RECORDED':({'outcome','reason_code'},set()),
 'ACCESSIBILITY_BLOCK_RECORDED':({'dimension'},set()),'VOLUNTARY_REUSE':(set(),{'task_ref'}),'BYPASS':({'reason_code'},{'alternative_ref'}),
 'ABANDONMENT':({'reason_code'},set()),'EPISODE_ENDED':({'instrumentation_terminal'},{'outcome_state'})}
HUMAN_FIELDS=('capture_review_burden_acceptable_confirmed_by_human','contribution_proposal_correction_by_human','correction_reason','future_reuse_intent','history_materially_helped_confirmed_by_human','history_reuse_judgment','human_next_action_change_judgment','human_usefulness_judgment','next_action_changed_confirmed_by_human','reentry_better_than_baseline_confirmed_by_human','reentry_better_than_baseline_judgment','representation_fit_judgment','trust_and_control_judgment','usefulness_confirmed_by_human','usefulness_judgment','voluntary_reuse_or_bypass','would_voluntarily_reuse_confirmed_by_human')
B6_HUMAN=frozenset(HUMAN_FIELDS)-{'correction_reason','history_reuse_judgment','human_next_action_change_judgment','human_usefulness_judgment','voluntary_reuse_or_bypass'}
BURDEN=('task_minutes','capture_minutes','review_and_correction_minutes','cognitive_load','switching_friction','privacy_concern','trust_or_control_loss','lock_in_dependence','error_recovery_cost')
B6_BURDEN=frozenset(BURDEN)-{'lock_in_dependence'}
ADDITIVE={'task_minutes','capture_minutes','review_and_correction_minutes','error_recovery_cost'}
CLAIM='Controlled-local custody/privacy/burden repair only; no human value, production security, legal compliance, product direction, release, merge, cutover, or owner admission.'
FORBIDDEN=('raw_content','raw_project','raw_text','private_payload','private_content','sealed_data','sealed_evaluator','secret','credential','password','access_token','api_key')

class Terminal(RuntimeError):
 def __init__(self,code,msg): super().__init__(msg); self.code=code

def cbytes(v):
 try:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
 except Exception as e:raise Terminal('NO_SAFE','noncanonical JSON') from e
def digest(v):return hashlib.sha256(cbytes(v)).hexdigest()
def time(v):
 try:d=datetime.fromisoformat(v.replace('Z','+00:00'))
 except Exception as e:raise Terminal('NO_SAFE','invalid time') from e
 if d.tzinfo is None:raise Terminal('NO_SAFE','timezone required')
def pointer(v):
 if not isinstance(v,Mapping) or not isinstance(v.get('locator'),str):raise Terminal('NO_SAFE','typed pointer required')
 if v.get('identity_mode')=='IMMUTABLE_CONTENT':
  h=v.get('sha256');
  if not isinstance(h,str) or len(h)!=64 or any(x not in '0123456789abcdef' for x in h):raise Terminal('NO_SAFE','sha256 required')
 elif v.get('identity_mode')=='MUTABLE_CURRENTNESS':
  if not v.get('revision_token') or not v.get('observed_at'):raise Terminal('REENTRY_REQUIRED','refresh pointer')
  time(v['observed_at'])
 else:raise Terminal('NO_SAFE','unknown pointer mode')
def rel(v):
 p=PurePosixPath(v)
 if not v or '\\' in v or p.is_absolute() or any(x in ('','.','..') for x in p.parts):raise Terminal('NO_SAFE','unsafe path')
 return p

def consent(subject,scopes,at):
 s=tuple(sorted(set(scopes)));time(at)
 if not subject or any(x not in SCOPES for x in s):raise Terminal('NO_SAFE','invalid consent')
 x={'subject_id':subject,'active_scopes':s,'at':at};return {'consent_id':'consent:'+digest(x)[:24],**x}
def store(store_id,subject,receipt):
 if receipt.get('subject_id')!=subject:raise Terminal('NO_SAFE','subject mismatch')
 return {'store_id':store_id,'subject_id':subject,'consent':dict(receipt),'records':{},'tombstones':{},'exports':{},'revocations':[]}
def scope(s,x):
 if x not in set(s['consent']['active_scopes']):raise Terminal('REENTRY_REQUIRED','missing scope '+x)
def forbidden(v):
 if isinstance(v,Mapping):
  for k,x in v.items():
   if any(y in str(k).casefold() for y in FORBIDDEN):return True
   if forbidden(x):return True
 if isinstance(v,list):return any(forbidden(x) for x in v)
 return False

def validate_event(kind,payload):
 schema=EVENT_SCHEMAS.get(kind)
 if not schema:raise Terminal('NO_SAFE','undeclared event')
 if not isinstance(payload,Mapping):raise Terminal('NO_SAFE','payload object required')
 req,opt=schema;k=set(payload)
 if req-k or k-req-opt:raise Terminal('NO_SAFE','payload schema mismatch')
 if forbidden(payload):raise Terminal('NO_SAFE','raw/private/sealed payload forbidden')
 for n in ('source_ref','action_ref','target_ref','task_ref','alternative_ref'):
  if n in payload:pointer(payload[n])
 if kind=='BURDEN_OBSERVED':
  d=payload['deltas']
  if not isinstance(d,Mapping) or not d or set(d)-set(BURDEN):raise Terminal('NO_SAFE','burden schema')
  if any(not isinstance(x,(int,float)) or isinstance(x,bool) or x<0 for x in d.values()):raise Terminal('NO_SAFE','burden value')
 if kind=='HUMAN_JUDGMENT_RECORDED':
  if payload.get('human_supplied') is not True:raise Terminal('RIGHT_CENSORED','human missing')
  f=payload.get('fields')
  if not isinstance(f,Mapping) or not f:raise Terminal('RIGHT_CENSORED','human fields missing')
  if set(f)-set(HUMAN_FIELDS):raise Terminal('NO_SAFE','human schema')

def capture(s,kind,key,payload,refs,at,human=False,parent_ids=(),retention_hold=None):
 validate_event(kind,payload);time(at);[pointer(x) for x in refs]
 cls='human' if kind=='HUMAN_JUDGMENT_RECORDED' else 'event';scope(s,'human_judgment_capture' if cls=='human' else 'local_operational_capture')
 if cls=='human' and not human:raise Terminal('RIGHT_CENSORED','explicit human input required')
 for parent in parent_ids:
  if parent not in s['records']:raise Terminal('REENTRY_REQUIRED','missing parent')
 ident={'store':s['store_id'],'kind':kind,'key':key,'payload':payload,'refs':refs,'at':at,'parent_ids':sorted(parent_ids)};rid='record:'+digest(ident)[:24]
 if rid in s['tombstones']:raise Terminal('NO_SAFE','tombstone reopen')
 r={'record_id':rid,'record_class':cls,'event_type':kind,'payload':dict(payload),'source_refs':list(refs),'created_at':at,'human':human,'parent_record_ids':sorted(parent_ids),'retention_hold':retention_hold,'claim_ceiling':CLAIM};r['record_digest']=digest(r)
 s['records'][rid]=r;return r

def burden_delta(s,oid,deltas,at,refs):return capture(s,'BURDEN_OBSERVED',oid,{'observation_id':oid,'deltas':dict(deltas)},refs,at)
def burden_ledger(s):
 totals={x:0.0 for x in BURDEN};seen={x:False for x in BURDEN};entries=[]
 for r in sorted(s['records'].values(),key=lambda x:(x['created_at'],x['record_id'])):
  if r['event_type']!='BURDEN_OBSERVED':continue
  d=r['payload']['deltas'];entries.append({'record_id':r['record_id'],'deltas':d})
  for k,v in d.items():seen[k]=True;totals[k]=totals[k]+float(v) if k in ADDITIVE else max(totals[k],float(v))
 values={k:(totals[k] if seen[k] else None) for k in BURDEN};return {'entries':entries,'values':values,'monotone':True,'ledger_digest':digest({'entries':entries,'values':values})}
def burden_terminal(s,ceiling):
 v=burden_ledger(s)['values'];return 'CAPTURE_COST_TOO_HIGH' if (v['capture_minutes'] or 0)+(v['review_and_correction_minutes'] or 0)>ceiling else 'INSTRUMENTATION_READY'

def human_adapter(v,source='B6'):
 allowed=B6_HUMAN if source=='B6' else frozenset(HUMAN_FIELDS)
 if not isinstance(v,Mapping) or set(v)-allowed:raise Terminal('NO_SAFE','human adapter input')
 out={k:v.get(k) for k in HUMAN_FIELDS};return {'source':source,'values':out,'missing':[k for k,x in out.items() if x is None],'imputed':False}
def burden_adapter(v,source='B6'):
 allowed=B6_BURDEN if source=='B6' else frozenset(BURDEN)
 if not isinstance(v,Mapping) or set(v)-allowed:raise Terminal('NO_SAFE','burden adapter input')
 out={k:(None if v.get(k) is None else float(v[k])) for k in BURDEN};return {'source':source,'values':out,'missing':[k for k,x in out.items() if x is None],'imputed':False}

def export(s,dest,purpose,classes,at,eid):
 if purpose not in PURPOSE_SCOPES:raise Terminal('NO_SAFE','unknown purpose')
 for x in PURPOSE_SCOPES[purpose]:scope(s,x)
 time(at);root=Path(dest);shutil.rmtree(root,ignore_errors=True);(root/'payload').mkdir(parents=True)
 records=[r for r in s['records'].values() if r['record_class'] in set(classes)];records.sort(key=lambda x:x['record_id'])
 payload={'records':records,'tombstones':sorted(s['tombstones'].values(),key=lambda x:x['record_id'])}
 files=[]
 for name,value in payload.items():
  p=root/'payload'/f'{name}.json';p.write_bytes(cbytes(value)+b'\n');files.append({'path':f'payload/{name}.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size})
 man={'schema_version':'gva06.f.ruv.export.v1','export_id':eid,'purpose':purpose,'required_scopes':list(PURPOSE_SCOPES[purpose]),'files':files,'record_ids':[x['record_id'] for x in records],'claim_ceiling':CLAIM};man['bundle_digest']=digest(man);(root/'MANIFEST.json').write_bytes(cbytes(man)+b'\n')
 s['exports'][eid]={'export_id':eid,'bundle_digest':man['bundle_digest'],'purpose':purpose,'record_ids':man['record_ids'],'state':'ACTIVE_LOCAL_HANDLE'};return man
def verify(root):
 root=Path(root);mp=root/'MANIFEST.json'
 if mp.is_symlink() or not mp.is_file():raise Terminal('NO_SAFE','manifest')
 man=json.loads(mp.read_text());x=dict(man);got=x.pop('bundle_digest',None)
 if digest(x)!=got:raise Terminal('NO_SAFE','manifest identity')
 declared=set()
 for e in man['files']:
  p=root/rel(e['path']);declared.add(e['path'])
  if p.is_symlink() or not p.is_file() or p.stat().st_size!=e['size'] or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:raise Terminal('NO_SAFE','payload')
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='MANIFEST.json'}
 if actual!=declared:raise Terminal('NO_SAFE','unmanifested')
 for r in json.loads((root/'payload/records.json').read_text()):
  y=dict(r);rd=y.pop('record_digest',None)
  if digest(y)!=rd or r.get('claim_ceiling')!=CLAIM:raise Terminal('NO_SAFE','record identity')
 return {'result':'PASS','bundle_digest':got}
def import_bundle(root,target,at):
 time(at);v=verify(root);man=json.loads((Path(root)/'MANIFEST.json').read_text())
 for x in man['required_scopes']:scope(target,x)
 imported=[]
 for r in json.loads((Path(root)/'payload/records.json').read_text()):
  if r['record_id'] in target['tombstones']:raise Terminal('NO_SAFE','tombstone import')
  if r['record_id'] not in target['records']:target['records'][r['record_id']]=r;imported.append(r['record_id'])
 return {'source_bundle_digest':v['bundle_digest'],'imported_record_ids':imported,'consent_expanded':False,'provenance_preserved':True}
def delete(s,ids,actor,reason,at,cascade=True):
 time(at);targets=set(ids)
 changed=True
 while cascade and changed:
  changed=False
  for rid,r in list(s['records'].items()):
   if rid not in targets and set(r.get('parent_record_ids',()))&targets:targets.add(rid);changed=True
 if not cascade and any(set(r.get('parent_record_ids',()))&targets for r in s['records'].values()):raise Terminal('REENTRY_REQUIRED','cascade disposition required')
 deleted=[]
 for rid in sorted(targets):
  r=s['records'].pop(rid,None)
  if not r:continue
  s['tombstones'][rid]={'record_id':rid,'record_digest':r['record_digest'],'deleted_at':at,'payload_retained':False,'secure_erase_claimed':False};deleted.append(rid)
 notices=[]
 for eid,h in s['exports'].items():
  if set(h['record_ids'])&set(deleted):
   n={'export_id':eid,'bundle_digest':h['bundle_digest'],'actor':actor,'reason':reason,'at':at,'local_handle_disposition':'REVOKED_LOCAL_HANDLE','external_copy_status':'OUTSIDE_LOCAL_AUTHORITY'};n['notice_digest']=digest(n);h['state']='REVOKED_LOCAL_HANDLE';notices.append(n)
 return {'deleted_record_ids':deleted,'cascaded_record_ids':sorted(set(deleted)-set(ids)),'export_revocation_notices':notices,'secure_erase_claimed':False}
def retention_sweep(s,ttl_days,now):
 time(now);expired=[];holds=[]
 current=datetime.fromisoformat(now.replace('Z','+00:00'))
 for rid,r in list(s['records'].items()):
  if r.get('retention_hold'):holds.append(rid);continue
  ttl=ttl_days.get(r['record_class'])
  if ttl is not None and (current-datetime.fromisoformat(r['created_at'].replace('Z','+00:00'))).total_seconds()>=ttl*86400:expired.append(rid)
 receipt=delete(s,expired,'retention','ttl',now) if expired else {'deleted_record_ids':[]}
 return {'terminal':'REENTRY_REQUIRED' if holds else 'PASS','expired_record_ids':expired,'unresolved_holds':holds,'delete_receipt':receipt}
def manifest():
 x={'artifact_id':'CustodyPrivacyBurdenRepair.v1','branch_id':'F.RUV.W3R.B2','canonical_authority':'CustodyPrivacyBurdenRepair.v1','ad_hoc_export_delete_paths':False,'fixed_findings':['F01','F02','F03','F04','F05','F06','F07','F08'],'claim_ceiling':CLAIM};x['artifact_digest']=digest(x);return x

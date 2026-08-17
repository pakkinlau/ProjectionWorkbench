"""Versioned privacy/portability repair over the v1 local kernel."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import hashlib, json, math, shutil, unicodedata
from pathlib import Path
from typing import Any, Mapping, Sequence
from . import privacy as legacy

PrivacyValidationError=legacy.PrivacyValidationError
EXPORT_SCHEMA_VERSION='project-semantics.export.v2'
PROJECTION_SCHEMA_VERSION='project-semantics.projection.v2'
REFERENCE_SCHEMA_VERSION='project-semantics.external-ref.v2'
PROJECT_SCHEMA_VERSION='project-semantics.kernel.v0'
STATES={'ACTIVE','EXPIRED','REVOKED','TOMBSTONED'}
MAX_MANIFEST_BYTES=1_000_000

def _now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def _dt(v,n):
 if not isinstance(v,str) or not v.strip(): raise PrivacyValidationError(f'{n} timestamp required')
 try: x=datetime.fromisoformat(v.replace('Z','+00:00'))
 except ValueError as e: raise PrivacyValidationError(f'invalid {n}') from e
 if x.tzinfo is None: raise PrivacyValidationError(f'{n} must be timezone-aware')
 return x.astimezone(timezone.utc)
def _loads(s):
 try: return json.loads(s,parse_constant=lambda x:(_ for _ in()).throw(PrivacyValidationError(f'non-finite JSON: {x}')))
 except PrivacyValidationError: raise
 except Exception as e: raise PrivacyValidationError('invalid portable JSON') from e
def validate_json_limits(v,*,max_depth=16,max_nodes=20_000,max_string_bytes=1_000_000):
 n=0
 def f(x,d):
  nonlocal n;n+=1
  if n>max_nodes: raise PrivacyValidationError('metadata node limit exceeded')
  if d>max_depth: raise PrivacyValidationError('metadata depth limit exceeded')
  if isinstance(x,str):
   if len(x.encode())>max_string_bytes: raise PrivacyValidationError('metadata string size limit exceeded')
  elif isinstance(x,Mapping):
   for k,y in x.items():
    if not isinstance(k,str): raise PrivacyValidationError('metadata object keys must be strings')
    f(k,d+1);f(y,d+1)
  elif isinstance(x,Sequence) and not isinstance(x,(str,bytes,bytearray)):
   for y in x:f(y,d+1)
  elif isinstance(x,float):
   if not math.isfinite(x): raise PrivacyValidationError('non-finite numbers are not portable JSON')
  elif x is not None and not isinstance(x,(bool,int)): raise PrivacyValidationError(f'unsupported metadata type: {type(x).__name__}')
 f(v,0)
def canonical_bytes(v):
 try:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
 except Exception as e:raise PrivacyValidationError('value is not canonical portable JSON') from e
def canonical_digest(v):return hashlib.sha256(canonical_bytes(v)).hexdigest()
def _fd(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()

def validate_external_reference(r,*,now=None,max_age_days=365,require_exchangeable=True):
 if r.get('schema_version') not in {REFERENCE_SCHEMA_VERSION,legacy.REFERENCE_SCHEMA_VERSION}:raise PrivacyValidationError('unsupported external reference schema')
 if not isinstance(r.get('locator'),str) or not r['locator'].strip() or len(r['locator'])>4096:raise PrivacyValidationError('external reference requires bounded locator')
 if r.get('identity_mode')=='IMMUTABLE_CONTENT':
  d=r.get('sha256')
  if not isinstance(d,str) or len(d)!=64 or any(c not in '0123456789abcdef' for c in d):raise PrivacyValidationError('immutable reference requires lowercase sha256')
  if r.get('mutable_currentness') is not None:raise PrivacyValidationError('immutable reference cannot carry mutable currentness')
  return
 if r.get('identity_mode')!='MUTABLE_CURRENTNESS':raise PrivacyValidationError('invalid identity_mode')
 c=r.get('mutable_currentness')
 if not isinstance(c,Mapping):raise PrivacyValidationError('mutable reference requires currentness')
 for k in ('observed_at','revision_token','refresh_policy'):
  if not isinstance(c.get(k),str) or not c[k].strip():raise PrivacyValidationError(f'mutable currentness requires {k}')
 token=c['revision_token']
 if token=='UNBOUND':raise PrivacyValidationError('UNBOUND revision token is not admissible')
 if require_exchangeable and (r.get('exchangeable') is False or token.startswith('LOCAL_ONLY:')):raise PrivacyValidationError('reference is local-only')
 a,b=_dt(c['observed_at'],'observed_at'),_dt(now or _now(),'now')
 if a>b+timedelta(minutes=5):raise PrivacyValidationError('reference observed_at is in future')
 if max_age_days>=0 and b-a>timedelta(days=max_age_days):
  rr=c.get('refresh_receipt')
  if not isinstance(rr,Mapping) or rr.get('revision_token')!=token:raise PrivacyValidationError('mutable reference is stale')
 if r.get('sha256') is not None:raise PrivacyValidationError('mutable reference cannot carry sha256')
def make_external_reference(*,locator,sha256=None,observed_at=None,revision_token=None,refresh_policy=None,refresh_receipt=None):
 if sha256 is not None:
  r={'schema_version':REFERENCE_SCHEMA_VERSION,'locator':locator,'identity_mode':'IMMUTABLE_CONTENT','sha256':sha256,'mutable_currentness':None,'exchangeable':True};validate_external_reference(r);return r
 o=observed_at or _now();local=revision_token is None;token=revision_token or 'LOCAL_ONLY:'+hashlib.sha256((locator+o).encode()).hexdigest()[:16]
 r={'schema_version':REFERENCE_SCHEMA_VERSION,'locator':locator,'identity_mode':'MUTABLE_CURRENTNESS','sha256':None,'exchangeable':not local,'mutable_currentness':{'observed_at':o,'revision_token':token,'refresh_policy':refresh_policy or 'EXPLICIT_RECHECK','refresh_receipt':dict(refresh_receipt) if refresh_receipt else None}}
 validate_external_reference(r,max_age_days=-1,require_exchangeable=not local);return r

def _identity(p):return {k:p.get(k) for k in ('schema_version','policy_ref','audience','visible','audit_summary','subject_approval_requirement','lifecycle','supersedes_projection_id','claim_ceiling')}
def _pid(p):return 'projection:'+canonical_digest(_identity(p))[:24]
def _state(p,now=None):
 l=p.get('lifecycle')
 if not isinstance(l,Mapping) or l.get('state') not in STATES:raise PrivacyValidationError('invalid projection lifecycle')
 if l['state']=='ACTIVE' and l.get('expires_at') and _dt(l['expires_at'],'expires_at')<=_dt(now or _now(),'now'):return 'EXPIRED'
 return l['state']
def validate_projection(p,*,now=None):
 validate_json_limits(p)
 if p.get('schema_version')!=PROJECTION_SCHEMA_VERSION:raise PrivacyValidationError('unsupported projection schema')
 if not isinstance(p.get('visible'),Mapping):raise PrivacyValidationError('projection visible must be object')
 a=p.get('audit_summary')
 if not isinstance(a,Mapping) or set(a)!={'omitted_count','redacted_count'} or any(not isinstance(a[k],int) or a[k]<0 for k in a):raise PrivacyValidationError('invalid audit summary')
 if p.get('canonical_history_mutated') is not False:raise PrivacyValidationError('canonical history mutation forbidden')
 if _state(p,now)!=p['lifecycle']['state']:raise PrivacyValidationError('stale projection expiry state')
 if p['lifecycle']['state']!='ACTIVE' and p['visible']:raise PrivacyValidationError('non-active projection must be metadata-only')
 if p.get('projection_id')!=_pid(p):raise PrivacyValidationError('projection identity mismatch')
def create_projection(project,policy,*,created_at=None):
 validate_json_limits(project)
 if not isinstance(policy.get('allowlist'),Mapping):raise PrivacyValidationError('recursive allowlist required')
 audit=legacy._ProjectionAudit([],[]);v=legacy._project_value(project,policy['allowlist'],policy.get('redactions',{}),audit,())
 if v is legacy._DROP:v={}
 c=created_at or _now();e=policy.get('expires_at');state='EXPIRED' if e and _dt(e,'expires_at')<=_dt(_now(),'now') else 'ACTIVE'
 if state!='ACTIVE':v={}
 p={'schema_version':PROJECTION_SCHEMA_VERSION,'policy_ref':policy['policy_id'],'audience':policy['audience'],'visible':v,'audit_summary':{'omitted_count':len(audit.omitted_paths),'redacted_count':len(audit.redacted_paths)},'omitted_paths':[f'<omitted:{len(audit.omitted_paths)}>'] if audit.omitted_paths else [],'redacted_paths':[f'<redacted:{len(audit.redacted_paths)}>'] if audit.redacted_paths else [],'subject_approval_requirement':policy.get('subject_approval_requirement','REQUIRED'),'lifecycle':{'state':state,'created_at':c,'expires_at':e,'currentness_policy':policy.get('currentness_policy','EXPLICIT_REFRESH'),'revocation':None,'tombstone':None,'transition_history':[]},'canonical_history_mutated':False,'claim_ceiling':'Derived selective view only; not canonical history, trust, capability, or admission.'}
 p['projection_id']=_pid(p);validate_projection(p);return p
def transition_projection(p,*,action,actor,reason,at=None):
 validate_projection(p);t=at or _now();q=_loads(canonical_bytes(p).decode());cur=q['lifecycle']['state'];dst={'EXPIRE':'EXPIRED','REVOKE':'REVOKED','TOMBSTONE':'TOMBSTONED'}.get(action)
 if dst is None:raise PrivacyValidationError('unsupported transition')
 allowed={'ACTIVE':{'EXPIRED','REVOKED','TOMBSTONED'},'EXPIRED':{'REVOKED','TOMBSTONED'},'REVOKED':{'TOMBSTONED'},'TOMBSTONED':set()};q['supersedes_projection_id']=p['projection_id']
 if dst in allowed[cur]:
  q['lifecycle']['state']=dst;q['lifecycle'].setdefault('transition_history',[]).append({'from':cur,'to':dst,'at':t,'actor':actor,'reason':reason})
  if dst=='REVOKED':q['lifecycle']['revocation']={'at':t,'actor':actor,'reason':reason}
  if dst=='TOMBSTONED':q['lifecycle']['tombstone']={'at':t,'actor':actor,'reason':reason}
 else:q['lifecycle']['last_rejected_transition']={'from':cur,'requested':dst,'at':t,'actor':actor,'reason':reason}
 if q['lifecycle']['state']!='ACTIVE':q['visible']={}
 q['projection_id']=_pid(q);validate_projection(q);return q

def _safe(s):return legacy._safe_relative_path(s)
def _key(p):return unicodedata.normalize('NFC',p.as_posix()).casefold()
def _refs(v):
 if isinstance(v,Mapping):
  if v.get('schema_version') in {REFERENCE_SCHEMA_VERSION,legacy.REFERENCE_SCHEMA_VERSION}:validate_external_reference(v)
  for x in v.values():_refs(x)
 elif isinstance(v,Sequence) and not isinstance(v,(str,bytes,bytearray)):
  for x in v:_refs(x)
def _project(v):
 if not isinstance(v,Mapping) or v.get('schema_version')!=PROJECT_SCHEMA_VERSION or not isinstance(v.get('project_ref'),Mapping) or not v['project_ref'].get('project_id'):raise PrivacyValidationError('invalid project payload')
 validate_json_limits(v);_refs(v)
def _mi(m):return {k:v for k,v in m.items() if k!='bundle_digest'}
def _meta(p):
 q=_loads(canonical_bytes(p).decode());q['visible']={};q['projection_id']=_pid(q);validate_projection(q);return q

def export_bundle(*,project,projections,destination,migration_disposition='CURRENT_SCHEMA',created_at=None):
 _project(project);root=Path(destination);shutil.rmtree(root,ignore_errors=True);(root/'payload/projections').mkdir(parents=True)
 fs={'payload/project.json':('project',project,PROJECT_SCHEMA_VERSION)}
 for p in projections:
  validate_projection(p);q=p if p['lifecycle']['state']=='ACTIVE' else _meta(p);rel=f"payload/projections/{q['projection_id'].replace(':','_')}.json";fs[rel]=('projection',q,PROJECTION_SCHEMA_VERSION)
 entries=[]
 for rel,(role,payload,schema) in sorted(fs.items()):
  path=root/_safe(rel);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical_bytes(payload)+b'\n');entries.append({'path':rel,'role':role,'schema_version':schema,'sha256':_fd(path),'size':path.stat().st_size})
 m={'schema_version':EXPORT_SCHEMA_VERSION,'created_at':created_at or _now(),'migration_disposition':migration_disposition,'project_schema_version':PROJECT_SCHEMA_VERSION,'projection_schema_version':PROJECTION_SCHEMA_VERSION,'files':entries,'limits':{'max_manifest_bytes':MAX_MANIFEST_BYTES,'max_files':512,'max_total_bytes':50_000_000,'max_json_depth':16},'security_policy':{'reject_unmanifested':True,'reject_symlinks':True,'reject_non_finite':True,'require_unique_normalized_paths':True,'validate_payload_roles':True,'validate_content_ids':True,'validate_currentness':True},'claim_ceiling':'Portable local export only; not hosted admission or source truth.'};m['bundle_digest']=canonical_digest(_mi(m));(root/'MANIFEST.json').write_bytes(canonical_bytes(m)+b'\n');return m
def _manifest(p):
 if p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_MANIFEST_BYTES:raise PrivacyValidationError('manifest missing or too large')
 m=_loads(p.read_text());validate_json_limits(m)
 if not isinstance(m,Mapping):raise PrivacyValidationError('manifest must be object')
 return dict(m)
def verify_bundle(source,*,max_files=512,max_total_bytes=50_000_000,max_json_depth=16):
 root=Path(source);m=_manifest(root/'MANIFEST.json')
 if m.get('schema_version')!=EXPORT_SCHEMA_VERSION or canonical_digest(_mi(m))!=m.get('bundle_digest'):raise PrivacyValidationError('manifest identity mismatch')
 sec=m.get('security_policy',{});req={'reject_unmanifested','reject_symlinks','reject_non_finite','require_unique_normalized_paths','validate_payload_roles','validate_content_ids','validate_currentness'}
 if any(sec.get(x)is not True for x in req):raise PrivacyValidationError('incomplete security policy')
 fs=m.get('files');limits=m.get('limits',{})
 if not isinstance(fs,list) or len(fs)>min(max_files,int(limits.get('max_files',max_files))):raise PrivacyValidationError('file count limit exceeded')
 keys=set();paths=set();projects=0
 for i in fs:
  rel=_safe(str(i.get('path','')));k=_key(rel)
  if k in keys:raise PrivacyValidationError('duplicate/colliding path')
  keys.add(k);paths.add(rel.as_posix());role=i.get('role');schema=PROJECT_SCHEMA_VERSION if role=='project' else PROJECTION_SCHEMA_VERSION if role=='projection' else None
  if schema is None or i.get('schema_version')!=schema:raise PrivacyValidationError('payload role/schema mismatch')
  if role=='project':projects+=1
 if projects!=1:raise PrivacyValidationError('exactly one project required')
 actual=set()
 for p in root.rglob('*'):
  if p.is_symlink():raise PrivacyValidationError('symlink rejected')
  if p.is_file() and p.name!='MANIFEST.json':actual.add(p.relative_to(root).as_posix())
 if actual!=paths:raise PrivacyValidationError('unmanifested or missing file')
 total=0;verified=[]
 for i in fs:
  rel=_safe(i['path']);p=root/rel;total+=p.stat().st_size
  if total>min(max_total_bytes,int(limits.get('max_total_bytes',max_total_bytes))):raise PrivacyValidationError('total size limit exceeded')
  if p.stat().st_size!=i.get('size') or _fd(p)!=i.get('sha256'):raise PrivacyValidationError('payload digest mismatch')
  v=_loads(p.read_text());validate_json_limits(v,max_depth=min(max_json_depth,int(limits.get('max_json_depth',max_json_depth))))
  if i['role']=='project':_project(v)
  else:
   validate_projection(v)
   if rel.name!=v['projection_id'].replace(':','_')+'.json':raise PrivacyValidationError('projection filename/id mismatch')
  verified.append(rel.as_posix())
 return {'schema_version':'project-semantics.bundle-verification.v2','bundle_digest':m['bundle_digest'],'verified_files':verified,'total_bytes':total,'migration_disposition':m.get('migration_disposition'),'result':'PASS'}
def import_bundle(source,destination,*,max_files=512,max_total_bytes=50_000_000,max_json_depth=16):
 a=verify_bundle(source,max_files=max_files,max_total_bytes=max_total_bytes,max_json_depth=max_json_depth);src=Path(source);dst=Path(destination)
 if dst.exists() and any(dst.iterdir()):raise PrivacyValidationError('clean-room destination must be empty')
 dst.mkdir(parents=True,exist_ok=True);m=_manifest(src/'MANIFEST.json')
 for i in m['files']:
  rel=_safe(i['path']);q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/rel,q)
 shutil.copyfile(src/'MANIFEST.json',dst/'MANIFEST.json');b=verify_bundle(dst,max_files=max_files,max_total_bytes=max_total_bytes,max_json_depth=max_json_depth)
 if a['bundle_digest']!=b['bundle_digest']:raise PrivacyValidationError('import changed bundle identity')
 return {'schema_version':'project-semantics.import-receipt.v2','source_bundle_digest':a['bundle_digest'],'imported_bundle_digest':b['bundle_digest'],'migration_disposition':b['migration_disposition'],'clean_room':True,'result':'PASS','claim_ceiling':'Verified local import only; not canonical admission.'}

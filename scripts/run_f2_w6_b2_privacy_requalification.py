from __future__ import annotations
import copy, hashlib, json, os, shutil, tempfile
from pathlib import Path
from project_semantics.privacy_v2 import *

def project(private_key='secret_diagnosis:HIV'):
 return {'schema_version':'project-semantics.kernel.v0','project_ref':{'project_id':'demo','title':'Demo',private_key:'positive','owner_or_custodian':'private-owner'},'source_links':[{'link_id':'s1','kind':'git','locator':'external://repo','content_identity':'sha256:abc','credentials':'token-secret'}],'episodes':[{'episode_id':'e1','outcome_state':'DONE','activities':[{'private_reason':'sealed'}]}]}
def policy(expires='2026-09-01T00:00:00Z'):
 return {'policy_id':'public-v1','audience':'public','allowlist':{'project_ref':{'project_id':True,'title':True},'source_links':{'*':{'link_id':True,'kind':True,'content_identity':True}},'episodes':{'*':{'episode_id':True,'outcome_state':True}}},'redactions':{},'subject_approval_requirement':'REQUIRED','currentness_policy':'EXPLICIT_REFRESH','expires_at':expires}
def blocked(fn):
 try:fn();return False
 except PrivacyValidationError:return True
def rewrite_manifest(root,mut,rehash=False):
 p=root/'MANIFEST.json';m=json.loads(p.read_text());mut(m)
 if rehash:m['bundle_digest']=canonical_digest({k:v for k,v in m.items() if k!='bundle_digest'})
 p.write_bytes(canonical_bytes(m)+b'\n')
def rewrite_entry(root,rel,payload):
 p=root/rel;p.write_bytes(canonical_bytes(payload)+b'\n');m=json.loads((root/'MANIFEST.json').read_text())
 for i in m['files']:
  if i['path']==rel:i['size']=p.stat().st_size;i['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
 m['bundle_digest']=canonical_digest({k:v for k,v in m.items() if k!='bundle_digest'});(root/'MANIFEST.json').write_bytes(canonical_bytes(m)+b'\n')
def run(output=None):
 rows=[]
 def add(cid,ok,detail):rows.append({'case_id':cid,'disposition':'PASS' if ok else 'FINDING','detail':detail})
 pr=create_projection(project(),policy(),created_at='2026-08-17T00:00:00Z');text=json.dumps(pr,sort_keys=True)
 add('RT01',not any(x in text for x in ['positive','private-owner','token-secret','sealed']),'private values absent')
 add('RT02','secret_diagnosis:HIV' not in text,'private field names absent')
 a=create_projection(project('private_A'),policy(),created_at='2026-08-17T00:00:00Z');b=create_projection(project('private_B'),policy(),created_at='2026-08-17T00:00:00Z');add('RT03',a['visible']!=b['visible'] or a['projection_id']==b['projection_id'],'private-only schema does not perturb public ID')
 stale=make_external_reference(locator='https://example.invalid/current',observed_at='2020-01-01T00:00:00Z',revision_token='etag:old');add('RT04',blocked(lambda:validate_external_reference(stale)),'stale mutable ref blocked')
 local=make_external_reference(locator='https://example.invalid/current');add('RT05',local['mutable_currentness']['revision_token']!='UNBOUND' and blocked(lambda:validate_external_reference(local)),'local-only unresolved ref cannot exchange')
 active=create_projection(project(),policy(),created_at='2026-08-17T00:00:00Z');rev=transition_projection(active,action='REVOKE',actor='owner',reason='withdraw',at='2026-08-18T00:00:00Z');add('RT06',transition_projection(rev,action='EXPIRE',actor='owner',reason='time',at='2026-08-19T00:00:00Z')['lifecycle']['state']=='REVOKED','revocation monotone')
 tomb=transition_projection(active,action='TOMBSTONE',actor='owner',reason='remove',at='2026-08-18T00:00:00Z');add('RT07',transition_projection(tomb,action='REVOKE',actor='owner',reason='withdraw',at='2026-08-19T00:00:00Z')['lifecycle']['state']=='TOMBSTONED','tombstone terminal')
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);revout=root/'rev';export_bundle(project=project(),projections=[rev],destination=revout,created_at='2026-08-17T00:00:00Z');rp=json.loads(next((revout/'payload/projections').glob('*.json')).read_text());add('RT08',not rp['visible'],'revoked export metadata-only')
  good=root/'good';export_bundle(project=project(),projections=[active],destination=good,created_at='2026-08-17T00:00:00Z')
  trav=root/'trav';shutil.copytree(good,trav);rewrite_manifest(trav,lambda m:m['files'].append({'path':'../escape.json','role':'projection','schema_version':PROJECTION_SCHEMA_VERSION,'sha256':'0'*64,'size':0}),True);add('RT09',blocked(lambda:verify_bundle(trav)),'traversal blocked')
  sym=root/'sym';shutil.copytree(good,sym);p=sym/'payload/project.json';p.unlink();os.symlink('/etc/hosts',p);add('RT10',blocked(lambda:verify_bundle(sym)),'symlink blocked')
  extra=root/'extra';shutil.copytree(good,extra);(extra/'unmanifested.bin').write_bytes(b'x'*2_000_000);add('RT11',blocked(lambda:verify_bundle(extra,max_total_bytes=100000)),'unmanifested resource blocked')
  deep=root/'deep';shutil.copytree(good,deep)
  def md(m):
   x={};c=x
   for _ in range(30):c['x']={};c=c['x']
   m['ignored']=x
  rewrite_manifest(deep,md);add('RT12',blocked(lambda:verify_bundle(deep)),'deep manifest blocked')
  tam=root/'tam';shutil.copytree(good,tam);(tam/'payload/project.json').write_text('{}\n');add('RT13',blocked(lambda:verify_bundle(tam)),'payload tamper blocked')
  meta=root/'meta';shutil.copytree(good,meta);rewrite_manifest(meta,lambda m:m.__setitem__('claim_ceiling','PROMOTED'));add('RT14',blocked(lambda:verify_bundle(meta)),'manifest metadata tamper blocked')
  schema=root/'schema';shutil.copytree(good,schema);rewrite_entry(schema,'payload/project.json',['not','project']);add('RT15',blocked(lambda:verify_bundle(schema)),'schema confusion blocked')
  dup=root/'dup';shutil.copytree(good,dup);rewrite_manifest(dup,lambda m:m['files'].append(copy.deepcopy(m['files'][0])),True);add('RT16',blocked(lambda:verify_bundle(dup)),'duplicate path blocked')
  past=create_projection(project(),policy('2020-01-01T00:00:00Z'),created_at='2019-01-01T00:00:00Z');add('RT17',past['lifecycle']['state']=='EXPIRED' and not past['visible'],'past expiry enforced')
  forged=copy.deepcopy(active);forged['visible']['project_ref']['title']='FORGED';add('RT18',blocked(lambda:export_bundle(project=project(),projections=[forged],destination=root/'forged')),'forged ID blocked')
  nan=project();nan['metric']=float('nan');add('RT19',blocked(lambda:export_bundle(project=nan,projections=[],destination=root/'nan')),'non-finite JSON blocked')
  rec=import_bundle(good,root/'clean');add('RT20',rec['source_bundle_digest']==rec['imported_bundle_digest'],'clean-room digest preserved')
 report={'schema_version':'gva06.f2.privacy-portability-requalification.v1','terminal':'QUALIFIED_AT_CONTROLLED_LOCAL_CEILING' if all(r['disposition']=='PASS' for r in rows) else 'REPAIR_REQUIRED','test_count':len(rows),'pass_count':sum(r['disposition']=='PASS' for r in rows),'finding_count':sum(r['disposition']!='PASS' for r in rows),'results':rows,'claim_boundary':'Controlled local privacy/portability requalification only.'}
 if output:Path(output).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 return report
if __name__=='__main__':
 import sys;print(json.dumps(run(sys.argv[1] if len(sys.argv)>1 else None),indent=2,sort_keys=True))

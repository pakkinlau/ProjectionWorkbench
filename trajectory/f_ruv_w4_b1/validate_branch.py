#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
C=json.loads((ROOT/'CARRIER.json').read_text())
encoded=(ROOT/'BranchEvidence.v1.json.gz.b64').read_text().strip()
gz=base64.b64decode(encoded,validate=True)
assert len(gz)==C['gzip_bytes']
assert hashlib.sha256(gz).hexdigest()==C['gzip_sha256']
raw=gzip.decompress(gz)
assert len(raw)==C['raw_bytes']
assert hashlib.sha256(raw).hexdigest()==C['raw_sha256']
E=json.loads(raw)
assert E['program_id']=='GVA06.F.repeat-use-value-discovery.v2'
assert E['branch_id']=='F.RUV.W4.B1'
assert E['terminal']=='RIGHT_CENSORED'
assert E['scientific_branch_final'] is False
T=E['project_a_trajectory']
assert T['qualified_target']=='sha256:b7d3d67c4d812fc28ffed2408fa41c96367fb99ce5cc1a6de77d5658709a6d9a'
assert T['real_episode_count']==1
assert T['minimum_real_episodes_for_longitudinal_claim']==3
assert T['delayed_reentry_observed'] is False
assert T['multiple_later_real_inquiries_observed'] is False
assert T['human_judgments_observed']=={}
assert T['human_judgments_imputed'] is False
assert T['human_repeat_use_value_supported'] is False
assert T['product_direction_frozen'] is True
assert T['branch_terminal']=='RIGHT_CENSORED'
assert E['admission_evidence_receipt']['max_evidence_rung']=='R1_HUMAN_BOUND_EPISODE'
assert E['admission_evidence_receipt']['outcome_judgment_present'] is False
assert E['source_pointer_manifest']['prior_wave_wrapper_embedded'] is False
assert E['source_pointer_manifest']['target_archive_embedded'] is False
assert E['source_pointer_manifest']['repository_clone_embedded'] is False
assert E['source_pointer_manifest']['virtual_environment_embedded'] is False
assert E['source_pointer_manifest']['dependencies_embedded'] is False
assert E['branch_completion_receipt']['completion_status']=='PASS_AT_CURRENT_CUTOFF_RIGHT_CENSORED'
assert E['branch_completion_receipt']['scientific_longitudinal_objective_complete'] is False
assert len(E['worker_returns'])==4
assert all(w['predecessor_payload_embedded_bytes']==0 for w in E['worker_returns'])
copy=dict(E); claimed=copy.pop('artifact_digest')
got=hashlib.sha256(json.dumps(copy,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
assert got==claimed,(got,claimed)
print(json.dumps({'branch_id':E['branch_id'],'terminal':E['terminal'],'real_episode_count':T['real_episode_count'],'target':T['qualified_target'],'artifact_digest':claimed,'validation':'PASS'},sort_keys=True))

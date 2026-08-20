#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    root=Path(__file__).resolve().parent
    x=json.loads((root/'Episode0002Pointer.v1.json').read_text())
    assert x['branch_id']=='F.RUV.W4C.B1'
    assert x['predecessor_head_sha']=='a3d2555a9e1afd4d41d477cfde2e5edba967ed83'
    assert x['qualified_target']=='sha256:b7d3d67c4d812fc28ffed2408fa41c96367fb99ce5cc1a6de77d5658709a6d9a'
    assert x['real_episode_count']==2 and x['minimum_real_episodes']==3
    assert x['delayed_reentry_observed'] is True
    assert x['human_judgments_captured']==0 and x['human_judgments_imputed'] is False
    assert x['protocol_invocation_counts_as_voluntary_reuse'] is False
    assert x['voluntary_reuse_observed'] is False
    assert x['human_repeat_use_value_supported'] is False
    assert x['product_direction']=='FROZEN' and x['wave_5_open'] is False
    assert x['terminal']=='RIGHT_CENSORED' and x['prior_payload_embedded'] is False
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'Episode0002Pointer.v1.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    report={'schema_version':'gva06.f.ruv.w4c.b1.github-validation.v1','branch_id':x['branch_id'],'status':'PASS','terminal':x['terminal'],'real_episode_count':2,'delayed_reentry_observed':True,'human_value_supported':False,'prior_payload_embedded':False}
    report['artifact_digest']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    (a.output/'validation-report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())

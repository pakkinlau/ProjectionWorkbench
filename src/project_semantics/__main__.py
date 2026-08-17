from __future__ import annotations
import argparse, json
from . import ValidationError, compose, create_projection, derive_lens, init_project, link_source, load_json, record_contribution, record_episode, run_witness, write_json

def main(argv=None):
    p=argparse.ArgumentParser(prog="pws"); s=p.add_subparsers(dest="command",required=True)
    q=s.add_parser("init"); q.add_argument("path"); q.add_argument("--project-id",required=True); q.add_argument("--title",required=True); q.add_argument("--canonical-location")
    for cmd in ("link","episode","contribution"):
        q=s.add_parser(cmd); q.add_argument("path"); q.add_argument("--record",required=True)
    q=s.add_parser("lens"); q.add_argument("path"); q.add_argument("--task",required=True); q.add_argument("--kind",choices=["continuation","contribution","collaboration"],required=True); q.add_argument("--output",required=True)
    q=s.add_parser("compose"); q.add_argument("--module-a",required=True); q.add_argument("--module-b",required=True); q.add_argument("--connector",required=True); q.add_argument("--output",required=True)
    q=s.add_parser("project"); q.add_argument("path"); q.add_argument("--policy",required=True); q.add_argument("--output",required=True)
    q=s.add_parser("witness"); q.add_argument("--fixture",required=True); q.add_argument("--workspace",required=True); q.add_argument("--output",required=True)
    a=p.parse_args(argv)
    try:
        if a.command=="init": r=init_project(a.path,project_id=a.project_id,title=a.title,canonical_location=a.canonical_location)
        elif a.command=="link": r=link_source(a.path,load_json(a.record))
        elif a.command=="episode": r=record_episode(a.path,load_json(a.record))
        elif a.command=="contribution": r=record_contribution(a.path,load_json(a.record))
        elif a.command=="lens": r=derive_lens(a.path,load_json(a.task),lens_kind=a.kind); write_json(a.output,r)
        elif a.command=="compose": r=compose(load_json(a.module_a),load_json(a.module_b),load_json(a.connector)); write_json(a.output,r)
        elif a.command=="project": r=create_projection(a.path,load_json(a.policy)); write_json(a.output,r)
        else: r=run_witness(a.fixture,a.workspace,a.output)
    except (ValidationError,OSError,json.JSONDecodeError) as e:
        print(f"ERROR: {e}"); return 2
    print(json.dumps(r,indent=2,sort_keys=True,ensure_ascii=False)); return 0
if __name__=="__main__": raise SystemExit(main())

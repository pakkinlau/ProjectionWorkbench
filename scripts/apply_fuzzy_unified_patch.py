#!/usr/bin/env python3
"""Apply a text-only unified diff with bounded fuzzy matching.

This helper exists for source-bound handoff patches whose predecessor blob set is
route-equivalent but not reachable from the current repository history. It never
applies binary patches and fails closed on ambiguous or low-similarity matches.
"""
from __future__ import annotations
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import argparse, re
HUNK_RE=re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
@dataclass
class Hunk:
 old_start:int; old_count:int; new_start:int; new_count:int; lines:list[str]
@dataclass
class FilePatch:
 old_path:str; new_path:str; hunks:list[Hunk]; new_file:bool=False; deleted_file:bool=False
def parse_patch(text:str)->list[FilePatch]:
 lines=text.splitlines(keepends=True); patches=[]; i=0
 while i<len(lines):
  if not lines[i].startswith('diff --git '):i+=1;continue
  m=re.match(r'diff --git a/(.+) b/(.+)\n?$',lines[i])
  if not m:raise ValueError(f'invalid diff header: {lines[i]!r}')
  fp=FilePatch(m.group(1),m.group(2),[]);i+=1
  while i<len(lines) and not lines[i].startswith('diff --git '):
   line=lines[i]
   if line.startswith('new file mode'):fp.new_file=True;i+=1;continue
   if line.startswith('deleted file mode'):fp.deleted_file=True;i+=1;continue
   if line.startswith('@@ '):
    hm=HUNK_RE.match(line)
    if not hm:raise ValueError(f'invalid hunk header: {line!r}')
    h=Hunk(int(hm.group(1)),int(hm.group(2) or 1),int(hm.group(3)),int(hm.group(4) or 1),[]);i+=1
    while i<len(lines) and not lines[i].startswith(('@@ ','diff --git ')):
     if lines[i].startswith((' ','+','-','\\')):h.lines.append(lines[i]);i+=1
     else:break
    fp.hunks.append(h);continue
   i+=1
  patches.append(fp)
 return patches
def blocks(h:Hunk)->tuple[list[str],list[str]]:
 old=[];new=[]
 for raw in h.lines:
  if raw.startswith('\\'):continue
  prefix,body=raw[0],raw[1:]
  if prefix in (' ','-'):old.append(body)
  if prefix in (' ','+'):new.append(body)
 return old,new
def exact_positions(haystack:list[str],needle:list[str])->list[int]:
 if not needle:return [0]
 n=len(needle);return [i for i in range(len(haystack)-n+1) if haystack[i:i+n]==needle]
def best_window(lines:list[str],old:list[str],expected:int)->tuple[int,int,float]:
 if not old:return max(0,min(expected,len(lines))),0,1.0
 old_text=''.join(old);nominal=len(old);min_len=max(1,nominal-max(3,nominal//5));max_len=min(len(lines),nominal+max(3,nominal//5));radius=max(80,nominal*3);lo=max(0,expected-radius);hi=min(len(lines),expected+radius);best=(-1,nominal,-1.0)
 for start in range(lo,hi+1):
  for size in range(min_len,max_len+1):
   if start+size>len(lines):break
   ratio=SequenceMatcher(None,old_text,''.join(lines[start:start+size]),autojunk=False).ratio();score=ratio-min(0.08,abs(start-expected)/max(1,len(lines))*0.08)
   if score>best[2]:best=(start,size,score)
 return best
def apply_file(root:Path,fp:FilePatch,min_similarity:float)->dict[str,object]:
 target=root/fp.new_path
 if fp.deleted_file:
  if target.exists():target.unlink()
  return {'path':fp.new_path,'mode':'deleted'}
 if fp.new_file:
  if target.exists():raise RuntimeError(f'new-file target already exists: {fp.new_path}')
  result=[]
  for h in fp.hunks:result.extend(blocks(h)[1])
  target.parent.mkdir(parents=True,exist_ok=True);target.write_text(''.join(result),encoding='utf-8');return {'path':fp.new_path,'mode':'created','hunks':len(fp.hunks)}
 if not target.is_file():raise RuntimeError(f'target missing: {fp.new_path}')
 current=target.read_text(encoding='utf-8').splitlines(keepends=True);offset=0;observations=[]
 for idx,h in enumerate(fp.hunks,1):
  old,new=blocks(h);expected=max(0,h.old_start-1+offset);positions=exact_positions(current,old)
  if len(positions)==1:start=positions[0];size=len(old);score=1.0;mode='exact'
  elif len(positions)>1:start=min(positions,key=lambda p:abs(p-expected));size=len(old);score=1.0;mode='exact-nearest'
  else:
   if h.old_start==1 and len(fp.hunks)==1:
    ratio=SequenceMatcher(None,''.join(old),''.join(current),autojunk=False).ratio()
    if ratio>=min_similarity:start=0;size=len(current);score=ratio;mode='full-file-fuzzy'
    else:start,size,score=best_window(current,old,expected);mode='window-fuzzy'
   else:start,size,score=best_window(current,old,expected);mode='window-fuzzy'
   if score<min_similarity:raise RuntimeError(f'low-similarity hunk {idx} for {fp.new_path}: {score:.3f} < {min_similarity:.3f}')
  current[start:start+size]=new;offset+=len(new)-size;observations.append({'hunk':idx,'mode':mode,'start':start,'old_size':size,'new_size':len(new),'similarity':round(score,4)})
 target.write_text(''.join(current),encoding='utf-8');return {'path':fp.new_path,'mode':'updated','hunks':observations}
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('patch');ap.add_argument('--root',default='.');ap.add_argument('--min-similarity',type=float,default=0.55);ap.add_argument('--report');ns=ap.parse_args();root=Path(ns.root).resolve();results=[apply_file(root,fp,ns.min_similarity) for fp in parse_patch(Path(ns.patch).read_text(encoding='utf-8'))]
 import json
 payload={'files':results,'patch':str(Path(ns.patch).resolve()),'root':str(root)};rendered=json.dumps(payload,indent=2,sort_keys=True)+'\n'
 if ns.report:Path(ns.report).write_text(rendered,encoding='utf-8')
 print(rendered,end='');return 0
if __name__=='__main__':raise SystemExit(main())

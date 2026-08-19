#!/usr/bin/env python3
"""Apply a text-only unified diff with bounded line-level fuzzy matching."""
from __future__ import annotations
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import argparse, json, re
HUNK_RE=re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
@dataclass
class Hunk: old_start:int; old_count:int; new_start:int; new_count:int; lines:list[str]
@dataclass
class FilePatch: old_path:str; new_path:str; hunks:list[Hunk]; new_file:bool=False; deleted_file:bool=False
def parse(text:str)->list[FilePatch]:
 lines=text.splitlines(keepends=True);out=[];i=0
 while i<len(lines):
  if not lines[i].startswith('diff --git '):i+=1;continue
  m=re.match(r'diff --git a/(.+) b/(.+)\n?$',lines[i]);
  if not m:raise ValueError(lines[i])
  fp=FilePatch(m.group(1),m.group(2),[]);i+=1
  while i<len(lines) and not lines[i].startswith('diff --git '):
   if lines[i].startswith('new file mode'):fp.new_file=True;i+=1;continue
   if lines[i].startswith('deleted file mode'):fp.deleted_file=True;i+=1;continue
   if lines[i].startswith('@@ '):
    hm=HUNK_RE.match(lines[i]);
    if not hm:raise ValueError(lines[i])
    h=Hunk(int(hm.group(1)),int(hm.group(2) or 1),int(hm.group(3)),int(hm.group(4) or 1),[]);i+=1
    while i<len(lines) and not lines[i].startswith(('@@ ','diff --git ')):
     if lines[i].startswith((' ','+','-','\\')):h.lines.append(lines[i]);i+=1
     else:break
    fp.hunks.append(h);continue
   i+=1
  out.append(fp)
 return out
def blocks(h:Hunk)->tuple[list[str],list[str]]:
 old=[];new=[]
 for raw in h.lines:
  if raw.startswith('\\'):continue
  p,b=raw[0],raw[1:]
  if p in (' ','-'):old.append(b)
  if p in (' ','+'):new.append(b)
 return old,new
def exact(h:list[str],n:list[str])->list[int]:
 if not n:return [0]
 k=len(n);return [i for i in range(len(h)-k+1) if h[i:i+k]==n]
def normalized(lines:list[str])->list[str]:return [x.rstrip() for x in lines]
def best(lines:list[str],old:list[str],expected:int)->tuple[int,int,float]:
 if not old:return max(0,min(expected,len(lines))),0,1.0
 nominal=len(old);delta=max(2,nominal//12);sizes=sorted({max(1,nominal-delta),nominal,min(len(lines),nominal+delta)});radius=max(50,nominal*2);lo=max(0,expected-radius);hi=min(len(lines),expected+radius);needle=normalized(old);winner=(-1,nominal,-1.0)
 for start in range(lo,hi+1):
  for size in sizes:
   if start+size>len(lines):continue
   ratio=SequenceMatcher(None,needle,normalized(lines[start:start+size]),autojunk=False).ratio();score=ratio-min(.08,abs(start-expected)/max(1,len(lines))*.08)
   if score>winner[2]:winner=(start,size,score)
 return winner
def apply_one(root:Path,fp:FilePatch,minimum:float)->dict[str,object]:
 target=root/fp.new_path
 if fp.deleted_file:
  if target.exists():target.unlink()
  return {'path':fp.new_path,'mode':'deleted'}
 if fp.new_file:
  if target.exists():raise RuntimeError(f'new target exists: {fp.new_path}')
  data=[]
  for h in fp.hunks:data.extend(blocks(h)[1])
  target.parent.mkdir(parents=True,exist_ok=True);target.write_text(''.join(data),encoding='utf-8');return {'path':fp.new_path,'mode':'created'}
 if not target.is_file():raise RuntimeError(f'missing target: {fp.new_path}')
 cur=target.read_text(encoding='utf-8').splitlines(keepends=True);offset=0;obs=[]
 for index,h in enumerate(fp.hunks,1):
  old,new=blocks(h);expected=max(0,h.old_start-1+offset);positions=exact(cur,old)
  if positions:start=min(positions,key=lambda p:abs(p-expected));size=len(old);score=1.;mode='exact'
  elif h.old_start==1 and len(fp.hunks)==1:
   score=SequenceMatcher(None,normalized(old),normalized(cur),autojunk=False).ratio()
   if score>=minimum:start=0;size=len(cur);mode='full-file-fuzzy'
   else:start,size,score=best(cur,old,expected);mode='window-fuzzy'
  else:start,size,score=best(cur,old,expected);mode='window-fuzzy'
  if score<minimum:raise RuntimeError(f'low similarity {fp.new_path} hunk {index}: {score:.3f}')
  cur[start:start+size]=new;offset+=len(new)-size;obs.append({'hunk':index,'mode':mode,'similarity':round(score,4),'start':start,'old_size':size,'new_size':len(new)})
 target.write_text(''.join(cur),encoding='utf-8');return {'path':fp.new_path,'mode':'updated','hunks':obs}
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('patch');ap.add_argument('--root',default='.');ap.add_argument('--min-similarity',type=float,default=.55);ap.add_argument('--report');ns=ap.parse_args();root=Path(ns.root).resolve();result={'root':str(root),'patch':str(Path(ns.patch).resolve()),'files':[apply_one(root,x,ns.min_similarity) for x in parse(Path(ns.patch).read_text(encoding='utf-8'))]};text=json.dumps(result,indent=2,sort_keys=True)+'\n';print(text,end='');
 if ns.report:Path(ns.report).write_text(text,encoding='utf-8')
 return 0
if __name__=='__main__':raise SystemExit(main())

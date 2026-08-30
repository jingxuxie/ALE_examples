import math,itertools,time
from fusion import Problem
from baseline import partition

class PairOptimizer:
 def __init__(self,c):self.c=c;self.p=Problem(c);self.last_stats=0
 def solve(self,blocks,force_first=(),force_last=()):
  p=self.p;W=p.cap;L=p.limit
  indices=sorted(i for b in blocks for i in b);n=len(indices)
  if n>2*L:return None
  union=0;old=0.
  for b in blocks:
   m=k=0
   for i in b:m|=p.masks[i];k|=p.kinds[i]
   union|=m;old+=p.cost(m,k,len(b))
  d=union.bit_count()
  if d>2*W:return None
  qs=[q for q in range(p.n) if union>>q&1];qmap={q:i for i,q in enumerate(qs)}
  loc={j:i for i,j in enumerate(indices)};ALL=(1<<n)-1;full=(1<<d)-1
  masks=[];kinds=[];anc=[];prev={};succ=[[] for _ in indices];desc=[0]*n
  for i,j in enumerate(indices):
   mask=sum(1<<qmap[q] for q in self.c['gates'][j]['qubits']);masks.append(mask);kinds.append(p.kinds[j])
   a=1<<i
   for q in self.c['gates'][j]['qubits']:
    if q in prev:a|=anc[prev[q]];succ[prev[q]].append(i)
    prev[q]=i
   anc.append(a)
  for i in range(n-1,-1,-1):
   a=1<<i
   for j in succ[i]:a|=desc[j]
   desc[i]=a
  aq=[0]*d;dq=[0]*d;qb=[0]*d;kt={1:0,2:0,4:0}
  for i,m in enumerate(masks):
   kt[kinds[i]]|=1<<i
   while m:
    x=m&-m;q=x.bit_length()-1;m-=x
    aq[q]|=anc[i];dq[q]|=desc[i];qb[q]|=1<<i
  at=[0]*(full+1);dt=at[:];gm=at[:];wc=at[:]
  for m in range(1,full+1):
   x=m&-m;r=m-x;q=x.bit_length()-1
   at[m]=at[r]|aq[q];dt[m]=dt[r]|dq[q];gm[m]=gm[r]|1<<qs[q];wc[m]=wc[r]+1
  ffirst=flast=0
  for i in force_first:ffirst|=anc[loc[i]]
  for i in force_last:flast|=desc[loc[i]]
  if ffirst&flast:return None
  kindopts=[]
  for typ in (1,2,4):
   if typ!=1 and not kt[typ]:continue
   # Constrain a specialized first/second block by moving every other kind.
   fa=fd=0
   if typ!=1:
    nb=ALL^kt[typ]
    while nb:
     x=nb&-nb;i=x.bit_length()-1;nb-=x;fa|=anc[i];fd|=desc[i]
   kindopts.append((typ,fa,fd))
  best=old;win=None;seen=set()
  def actual(b):
   m=k=0;out=[]
   while b:
    x=b&-b;i=x.bit_length()-1;b-=x;j=indices[i];m|=p.masks[j];k|=kinds[i];out.append(j)
   return p.cost(m,k,len(out)),out
  for S in range(1,full+1):
   if wc[S]>W:continue
   FL=dt[full^S]|flast
   if FL.bit_count()>L or FL&ffirst:continue
   T0=0
   for q in range(d):
    if qb[q]&FL:T0|=1<<q
   if wc[T0]>W:continue
   available=full^T0;spare=W-wc[T0]
   # Only optional qubits already present in the first block can overlap.
   extra=[1<<q for q in range(d) if available>>q&1]
   for ne in range(min(spare,len(extra))+1):
    for comb in itertools.combinations(extra,ne):
     T=T0|sum(comb)
     if not T or (S|T)!=full:continue
     FF=at[full^T]|ffirst
     if FF&FL or FF.bit_count()>L:continue
     for k1,ka1,kd1 in kindopts:
      fl=FL|kd1
      if fl.bit_count()>L or FF&fl:continue
      for k2,ka2,kd2 in kindopts:
       ff=FF|ka2
       if ff&fl:continue
       lo=max(ff.bit_count(),n-L,1);hi=min(n-fl.bit_count(),L,n-1)
       if lo>hi:continue
       e1=1<<(wc[S] if k1 in(2,4) else 2*wc[S]);e2=1<<(wc[T] if k2 in(2,4) else 2*wc[T])
       c=lo if e1>e2 else hi
       est=p.cost(gm[S],k1,c)+p.cost(gm[T],k2,n-c)
       if est>=best-1e-7:continue
       first=ff;rest=ALL^fl^ff;need=c-first.bit_count()
       # FF is an ideal and FL is a filter; append an ordered prefix of the flexible gates.
       while need:
        x=rest&-rest;rest-=x;first|=x;need-=1
       if first in seen:continue
       seen.add(first)
       ca,ba=actual(first);cb,bb=actual(ALL^first)
       if ca+cb<best-1e-7:best=ca+cb;win=[ba,bb]
  self.last_stats=len(seen)
  # One block may be better as well.
  if d<=W and n<=L:
   k=0
   for x in kinds:k|=x
   co=p.cost(union,k,n)
   if co<best-1e-7 and not(force_first or force_last):best=co;win=[indices]
  if win is None:return None
  return best,win
 def run(self,blocks,passes=2,span=1,deadline=math.inf):
  bs=[b[:] for b in blocks]
  for iteration in range(passes):
   changed=False
   for window in (3,2):
    for s in range(len(bs)-window,-1,-1) if iteration%2 else range(len(bs)-window+1):
     if time.monotonic()>deadline:break
     if s+window>len(bs):continue
     bb=bs[s:s+window]
     if self.c['gates'][bb[0][0]]['epoch']!=self.c['gates'][bb[-1][0]]['epoch']:continue
     z=self.solve(bb)
     if z:
      bs[s:s+window]=z[1];changed=True
   if not changed:break
  return partition(self.c,[i for b in bs for i in b])

 def distant(self,blocks,passes=1,deadline=math.inf):
  bs=[b[:] for b in blocks];p=self.p;children=[[] for _ in p.g]
  for i,pp in enumerate(p.parents):
   for j in pp:children[j].append(i)
  for it in range(passes):
   pos={i:s for s,b in enumerate(bs) for i in b};pairs=[]
   for s in range(len(bs)):
    for t in range(s+2,len(bs)):
     if self.c['gates'][bs[s][0]]['epoch']!=self.c['gates'][bs[t][0]]['epoch']:continue
     m1=m2=0
     for i in bs[s]:m1|=p.masks[i]
     for i in bs[t]:m2|=p.masks[i]
     if (m1|m2).bit_count()>2*p.cap:continue
     if t-s>12 and not m1&m2:continue
     pairs.append(((m1|m2).bit_count(),len(bs[s])+len(bs[t]),t-s,s,t))
   changed=False
   for _,_,_,s,t in sorted(pairs):
    if time.monotonic()>deadline:break
    if not bs[s] or not bs[t]:continue
    FF=[];FL=[]
    for i in bs[s]+bs[t]:
     if any(s<pos[j]<t for j in children[i]):FF.append(i)
     if any(s<pos[j]<t for j in p.parents[i]):FL.append(i)
    z=self.solve([bs[s],bs[t]],FF,FL)
    if z:
     bs[s]=z[1][0];bs[t]=z[1][1] if len(z[1])==2 else []
     for i in bs[s]:pos[i]=s
     for i in bs[t]:pos[i]=t
     changed=True
   bs=[b for b in bs if b]
   if not changed:break
  return partition(self.c,[i for b in bs for i in b])

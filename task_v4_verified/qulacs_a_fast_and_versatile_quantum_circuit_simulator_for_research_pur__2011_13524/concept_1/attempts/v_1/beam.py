import math,time,heapq
from fusion import Problem
from baseline import partition

class BeamPlanner:
 def __init__(self,c):self.c=c;self.p=Problem(c)
 def epoch(self,ii,incumbent,beam=24,branch=16,support_beam=3,weight=0.,scale=1.,resource=False,prices=None,cut=False,deadline=math.inf):
  p=self.p;N=len(ii);L=p.limit;W=p.cap;ALL=(1<<N)-1
  local={j:i for i,j in enumerate(ii)};masks=[p.masks[j] for j in ii];kinds=[p.kinds[j] for j in ii]
  parents=[[local[j] for j in p.parents[i] if j in local] for i in ii]
  pb=[sum(1<<j for j in pp) for pp in parents];children=[[] for _ in ii];qb=[0]*p.n
  a2=a3=0
  for i,m in enumerate(masks):
   for j in parents[i]:children[j].append(i)
   for q in range(p.n):
    if m>>q&1:qb[q]|=1<<i
   if m.bit_count()==2:a2|=1<<i
   if m.bit_count()==3:a3|=1<<i
  def convert(bb):
   out=[]
   for b in bb:
    row=[]
    while b:
     x=b&-b;b-=x;row.append(ii[x.bit_length()-1])
    out.append(row)
   return out
  def costblocks(bb):
   z=0
   for b in bb:
    m=k=0
    for i in b:m|=p.masks[i];k|=p.kinds[i]
    z+=p.cost(m,k,len(b))
   return z
  bestcost=costblocks(incumbent);bestblocks=incumbent
  minapp=min(p.app.values())
  weights=[(1+weight*(m.bit_count()-1))*(p.cost(m,k,1)/minapp if resource else 1.) for m,k in zip(masks,kinds)]
  if prices is not None:weights=[prices[j] for j in ii]
  unit=bestcost/sum(weights)*scale
  expandcap=W
  if cut and sum(k in (2,4) for k in kinds)<.65*N:
   while expandcap>max(m.bit_count() for m in masks) and p.cost((1<<expandcap)-1,1,L)/L>1.15*bestcost/N:
    expandcap-=1
  evalstates=0;cache={}
  def actions(done):
   nonlocal evalstates
   if done in cache:return cache[done]
   evalstates+=1;remaining=ALL^done;front=0
   for b in qb:
    x=b&remaining;front|=x&-x
   todo=[]
   while front:
    x=front&-front;front-=x;i=x.bit_length()-1
    if not pb[i]&remaining:todo.append(i)
   req={};rk={};anc={};grouped={};gd={};gp={};queued=set(todo)
   while todo:
    i=todo.pop();m=masks[i];k=kinds[i];a=1<<i
    for j in parents[i]:
     if not done>>j&1:m|=req[j];k|=rk[j];a|=anc[j]
    if m.bit_count()>W or a.bit_count()>L:continue
    req[i]=m;rk[i]=k;anc[i]=a;grouped[m]=grouped.get(m,0)|(1<<i)
    if k==2:gd[m]=gd.get(m,0)|(1<<i)
    if k==4:gp[m]=gp.get(m,0)|(1<<i)
    for j in children[i]:
     if j not in queued and all(done>>z&1 or z in req for z in parents[j]):todo.append(j);queued.add(j)
   seeds=list(grouped);levels=[set() for _ in range(W+1)];mcache={};bcache={}
   def assess(S):
    if S in mcache:return mcache[S]
    sub=S;b=d=r=0
    while sub:b|=grouped.get(sub,0);d|=gd.get(sub,0);r|=gp.get(sub,0);sub=(sub-1)&S
    best=math.inf
    for B in (b,d,r):
     if not B:continue
     if B.bit_count()>L:
      tmp=B;B=0
      for _ in range(L):x=tmp&-tmp;tmp-=x;B|=x
     if B not in bcache:
      m=k=0;tmp=B;wt=0.
      while tmp:x=tmp&-tmp;tmp-=x;i=x.bit_length()-1;m|=masks[i];k|=kinds[i];wt+=weights[i]
      n=B.bit_count();v=p.cost(m,k,n)
      bcache[B]=(v,B,n,wt)
     v,B,n,wt=bcache[B];score=v/wt
     if score<best:best=score
    mcache[S]=best;return best
   for m in seeds:levels[m.bit_count()].add(m)
   for w in range(1,W):
    for s in sorted(levels[w],key=assess)[:support_beam]:
     for m in seeds:
      u=s|m;wc=u.bit_count()
      if w<wc<=expandcap:levels[wc].add(u)
   for s in levels[W]:assess(s)
   if expandcap<W:
    # A dense-kernel width bound must not suppress cheap wide diagonal or
    # permutation blocks.  Grow those using homogeneous dependency closures.
    for homogeneous in (gd,gp):
     if len(homogeneous)<2:continue
     pureseeds=list(homogeneous);purelevels=[set() for _ in range(W+1)]
     for m in pureseeds:purelevels[m.bit_count()].add(m)
     for w in range(1,W):
      for ss in sorted(purelevels[w],key=assess)[:support_beam]:
       for m in pureseeds:
        u=ss|m;wc=u.bit_count()
        if w<wc<=W:purelevels[wc].add(u)
     for ss in purelevels[W]:assess(ss)
   # Keep complementary candidates: high efficiency and high packed operation count.
   opts=list(bcache.values());opts.sort(key=lambda a:(a[0]/a[3],-a[2]))
   selected=opts[:branch]
   if len(opts)>branch:
    ss={a[1] for a in selected}
    for a in sorted(opts,key=lambda a:(-a[2],a[0]))[:branch//2]:
     if a[1] not in ss:selected.append(a)
   if len(cache)<15000:cache[done]=selected
   return selected
  states=[(0.,0.,0,None,0.)];seen={0:0.};depth=0
  search_start=time.monotonic()
  while states and time.monotonic()<deadline:
   depth+=1;next_states={}
   for _,co,done,path,covered in states:
    for v,b,n,wt in actions(done):
     nc=co+v;nd=done|b
     if nc>=bestcost-1e-7:continue
     if nd==ALL:
      bb=[b];pa=path
      while pa is not None:pa,ob=pa;bb.append(ob)
      bestcost=nc;bestblocks=convert(bb[::-1]);continue
     rem=N-nd.bit_count()
     if nc+((rem+L-1)//L)*minapp>=bestcost-1e-7:continue
     if nc>=seen.get(nd,math.inf)-1e-7:continue
     seen[nd]=nc
     score=nc-unit*(covered+wt)
     next_states[nd]=(score,nc,nd,(path,b),covered+wt)
    if time.monotonic()>deadline:break
   effective_beam=beam
   if math.isfinite(deadline) and evalstates>8:
    now=time.monotonic();per_state=(now-search_start)/evalstates
    layers_left=max(1,len(incumbent)-depth)
    effective_beam=max(2,min(beam,int(max(0.,deadline-now)/(per_state*layers_left*1.15+1e-9))))
   states=heapq.nsmallest(effective_beam,next_states.values(),key=lambda a:a[0])
  # Anytime completion: a scheduled ideal can always be followed by the
  # incumbent with those gates removed.  Repartitioning that legal order
  # makes useful partial searches available even at the time limit.
  for _,co,done,path,covered in states[:3]:
   prefix=[];pa=path
   while pa is not None:pa,ob=pa;prefix.append(ob)
   prefix=convert(prefix[::-1])
   tail=[[i for i in b if not done>>local[i]&1] for b in incumbent]
   order=[i for b in prefix+tail for i in b]
   z=p.partition(order)
   if z[0]<bestcost-1e-7:bestcost,bestblocks=z
  self.last_states=evalstates
  return bestcost,bestblocks
 def run(self,blocks,beam=24,branch=16,weight=0.,scale=1.,resource=False,prices=None,cut=False,deadline=math.inf):
  result=[];total=0;num=0;remaining_operations=self.p.N
  for ep,ii in sorted(self.p.epochs.items()):
   inc=[b for b in blocks if self.c['gates'][b[0]]['epoch']==ep]
   epoch_deadline=deadline
   if math.isfinite(deadline):
    now=time.monotonic();epoch_deadline=now+max(0.,deadline-now)*len(ii)/remaining_operations
   z=self.epoch(ii,inc,beam=beam,branch=branch,weight=weight,scale=scale,resource=resource,prices=prices,cut=cut,deadline=epoch_deadline)
   remaining_operations-=len(ii)
   total+=z[0];result.extend(z[1]);num+=self.last_states
  self.last_states=num
  return self.p.partition([i for b in result for i in b])

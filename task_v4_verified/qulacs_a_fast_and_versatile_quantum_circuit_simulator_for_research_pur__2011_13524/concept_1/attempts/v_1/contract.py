import heapq,math,random,time
from fusion import Problem
from baseline import partition

class Contractor:
 def __init__(self,c,alpha=0.,beta=0.,seed=0,deadline=math.inf):
  self.deadline=deadline;self.p=Problem(c);self.c=c;self.W=self.p.cap;self.L=self.p.limit
  self.alpha=alpha;self.beta=beta;self.rng=random.Random(seed);self.noise=0. if seed==0 else .08
 def epoch(self,indices):
  p=self.p
  nodes={i:[p.masks[i],p.kinds[i],1,p.cost(p.masks[i],p.kinds[i],1),[i]] for i in indices}
  parents={i:set(p.parents[i]) for i in indices};children={i:set() for i in indices}
  for i,pp in parents.items():
   for j in pp:children[j].add(i)
  order=indices[:];position={i:j for j,i in enumerate(order)}
  heap=[];serial=len(p.g);phase=0
  def push(a,b):
   if a==b:return
   aa=nodes[a];bb=nodes[b];m=aa[0]|bb[0];n=aa[2]+bb[2];w=m.bit_count()
   if w>self.W or n>self.L:return
   cost=p.cost(m,aa[1]|bb[1],n);gain=aa[3]+bb[3]-cost
   if gain<=1e-8:return
   score=gain*n**self.beta/w**self.alpha
   if self.noise:score*=self.rng.uniform(1-self.noise,1+self.noise)
   heapq.heappush(heap,(-score,min(a,b),max(a,b)))
  for a in indices:
   for b in children[a]:push(a,b)
  while True:
   if time.monotonic()>self.deadline:break
   if not heap:
    if phase:break
    phase=1
    oo=list(nodes)
    for j,a in enumerate(oo):
     for b in oo[j+1:]:push(a,b)
    if not heap:break
   _,a,b=heapq.heappop(heap)
   if a not in nodes or b not in nodes:continue
   if position[a]>position[b]:a,b=b,a
   # Find every intermediate node on a dependency path from a to b.
   upper=position[b];lower=position[a]
   desc={a};todo=[a]
   while todo:
    x=todo.pop()
    for y in children[x]:
     if position[y]<=upper and y not in desc:desc.add(y);todo.append(y)
   merge={a,b}
   if b in desc:
    todo=[b]
    while todo:
     x=todo.pop()
     for y in parents[x]:
      if y in desc and y not in merge:merge.add(y);todo.append(y)
   m=k=n=0;old=0.;bb=[]
   for x in merge:
    xx=nodes[x];m|=xx[0];k|=xx[1];n+=xx[2];old+=xx[3];bb.extend(xx[4])
   if m.bit_count()>self.W or n>self.L:continue
   cost=p.cost(m,k,n)
   if cost>=old-1e-8:continue
   new=serial;serial+=1
   pp=set();cc=set()
   for x in merge:pp.update(parents[x]);cc.update(children[x])
   pp-=merge;cc-=merge
   for x in pp:children[x].difference_update(merge);children[x].add(new)
   for x in cc:parents[x].difference_update(merge);parents[x].add(new)
   for x in merge:del nodes[x],parents[x],children[x]
   nodes[new]=[m,k,n,cost,bb];parents[new]=pp;children[new]=cc
   # Preserve the old order as far as possible when topologically sorting the quotient.
   priority=position[a]
   position[new]=priority
   indeg={x:len(parents[x]) for x in nodes}
   ready=[(position[x],x) for x in nodes if indeg[x]==0];heapq.heapify(ready);order=[]
   while ready:
    _,x=heapq.heappop(ready);order.append(x)
    for y in children[x]:
     indeg[y]-=1
     if indeg[y]==0:heapq.heappush(ready,(position[y],y))
   assert len(order)==len(nodes)
   position={x:i for i,x in enumerate(order)}
   if phase:
    for x in nodes:
     if x!=new:push(new,x)
   else:
    for x in pp|cc:push(new,x)
  return [sorted(nodes[x][4]) for x in order]
 def run(self):
  blocks=[]
  for ep,ii in sorted(self.p.epochs.items()):blocks.extend(self.epoch(ii))
  return self.p.partition([i for b in blocks for i in b])

def plan(c):
 from improve import improve
 win=(math.inf,None)
 for a,b in [(0,0),(1,0),(0,.5),(1,.5)]:
  z=Contractor(c,a,b).run();z=improve(c,z[1])
  if z[0]<win[0]:win=z
 return win[1]

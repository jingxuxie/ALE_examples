import math,random,time
from fusion import Problem

class Local:
 def __init__(self,case,blocks):
  self.deadline=math.inf;self.p=Problem(case);self.c=case;self.N=self.p.N;self.L=self.p.limit;self.W=self.p.cap
  self.bs=[set(b) for b in blocks];self.B=len(blocks)
  self.mask=[0]*self.B;self.kind=[0]*self.B;self.costs=[0.]*self.B
  self.pos=[0]*self.N
  self.parents=self.p.parents;self.children=[[] for _ in range(self.N)]
  for i,pp in enumerate(self.parents):
   for j in pp:self.children[j].append(i)
  self.epoch=[]
  for j,b in enumerate(self.bs):
   self.epoch.append(case['gates'][next(iter(b))]['epoch'])
   for i in b:self.pos[i]=j
   self.update(j)
 def update(self,j):
  m=k=0
  for i in self.bs[j]:m|=self.p.masks[i];k|=self.p.kinds[i]
  self.mask[j]=m;self.kind[j]=k
  self.costs[j]=self.p.cost(m,k,len(self.bs[j])) if m else 0.
 def targetcost(self,i,j):
  if len(self.bs[j])>=self.L:return math.inf
  m=self.mask[j]|self.p.masks[i]
  if m.bit_count()>self.W:return math.inf
  return self.p.cost(m,self.kind[j]|self.p.kinds[i],len(self.bs[j])+1)
 def bounds(self,i):
  return max((self.pos[p] for p in self.parents[i]),default=0),min((self.pos[p] for p in self.children[i]),default=self.B-1)
 def move(self,i,s,t):
  self.bs[s].remove(i);self.bs[t].add(i);self.pos[i]=t;self.update(s);self.update(t)
 def eliminate(self,s,mode=0):
  if not self.bs[s]:return False
  before=self.costs[s];orig={};moves=[];remaining=self.bs[s].copy();total_extra=0
  # For an empty block the decrease in launch cost can pay for locally uphill moves.
  while remaining:
   if time.monotonic()>self.deadline:break
   options=[]
   for i in remaining:
    lo,hi=self.bounds(i)
    for t in range(lo,hi+1):
     if t==s or not self.bs[t] or self.epoch[t]!=self.epoch[s]:continue
     tc=self.targetcost(i,t);extra=tc-self.costs[t]
     if math.isfinite(extra):
      key=extra
      if mode==1:key+=abs(t-s)*1e-6
      elif mode==2:key-=len(self.bs[t])*1e-5
      options.append((key,i,t,extra))
   if not options:break
   key,i,t,extra=min(options)
   if t not in orig:orig[t]=self.costs[t]
   moves.append((i,s,t));self.move(i,s,t);remaining.remove(i)
   total_extra+=extra
  if not remaining and total_extra<before-1e-7:
   return True
  for i,s,t in reversed(moves):self.move(i,t,s)
  return False
 def single_moves(self,rev=False):
  gain=0
  for i in (range(self.N-1,-1,-1) if rev else range(self.N)):
   if time.monotonic()>self.deadline:break
   s=self.pos[i];lo,hi=self.bounds(i);old=self.costs[s]
   self.bs[s].remove(i);self.update(s);saving=old-self.costs[s]
   best=(1e-7,None)
   for t in range(lo,hi+1):
    if t==s or not self.bs[t] or self.epoch[t]!=self.epoch[s]:continue
    tc=self.targetcost(i,t)
    delta=saving-(tc-self.costs[t])
    if delta>best[0]:best=(delta,t)
   self.bs[s].add(i);self.update(s)
   if best[1] is not None:
    self.move(i,s,best[1]);gain+=best[0]
  return gain
 def run(self,passes=3,deadline=math.inf):
  self.deadline=deadline
  for iteration in range(passes):
   old=sum(self.costs)
   self.single_moves(iteration%2)
   for s in sorted(range(self.B),key=lambda s:(len(self.bs[s]),-self.costs[s])):
    if time.monotonic()>deadline:break
    if self.bs[s]:self.eliminate(s,iteration%3)
   if old-sum(self.costs)<1e-7:break
  return sum(self.costs),[sorted(b) for b in self.bs if b]

def improve(case,blocks,passes=3,deadline=math.inf):return Local(case,blocks).run(passes,deadline)

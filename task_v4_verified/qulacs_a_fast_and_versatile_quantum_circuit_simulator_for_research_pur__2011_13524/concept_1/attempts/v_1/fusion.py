import math, json, sys, time
from pathlib import Path
from baseline import plan as baseline_plan, partition

class Problem:
 def __init__(self,case,reverse=False):
  self.case=case; self.n=case['n_qubits']; self.cap=case['max_block_qubits']; self.limit=case['max_block_operations']
  g=case['gates']; self.g=g; self.N=len(g)
  self.masks=[sum(1<<q for q in x['qubits']) for x in g]
  self.kinds=[{'dense':1,'diagonal':2,'permutation':4}[x['kind']] for x in g]
  self.epochs={}
  for i,x in enumerate(g):self.epochs.setdefault(x['epoch'],[]).append(i)
  self.parents=[[] for _ in g]; prev={}
  for i in (range(len(g)-1,-1,-1) if reverse else range(len(g))):
   self.parents[i]=list({prev[q] for q in g[i]['qubits'] if q in prev and g[prev[q]]['epoch']==g[i]['epoch']})
   for q in g[i]['qubits']:prev[q]=i
  self.reverse=reverse
  h=case['hardware']; self.build=h['build']
  self.app={}
  for w in range(1,self.cap+1):
   for s in (False,True):
    for q in range(self.n):
     stride=1+h['stride_penalty']*max(0,q-h['cache_qubits'])
     self.app[w,s,q]=case['repetitions']*(h['launch']+max(h['memory']*stride,h['compute']*(1 if s else 1<<w)))
 def cost(self,mask,kind,count):
  w=mask.bit_count(); s=kind in (2,4); q=(mask&-mask).bit_length()-1
  return self.app[w,s,q]+self.build*(count-1)*(1<<(w if s else w*2))


 def partition(self,order):
  count=len(order);best=[math.inf]*(count+1);following=[0]*count;best[count]=0.
  masks=self.masks;kinds=self.kinds;gates=self.g;W=self.cap;L=self.limit;app=self.app;build=self.build
  for start in range(count-1,-1,-1):
   mask=kind=0;epoch=gates[order[start]]["epoch"];value=math.inf;end=start+1
   for stop in range(start,min(count,start+L)):
    index=order[stop]
    if gates[index]["epoch"]!=epoch:break
    mask|=masks[index];kind|=kinds[index];w=mask.bit_count()
    if w>W:break
    spec=kind in (2,4);minimum=(mask&-mask).bit_length()-1
    candidate=app[w,spec,minimum]+build*(stop-start)*(1<<(w if spec else 2*w))+best[stop+1]
    if candidate<value:value=candidate;end=stop+1
   best[start]=value;following[start]=end
  blocks=[];start=0
  while start<count:
   stop=following[start];blocks.append(order[start:stop]);start=stop
  return best[0],blocks

 def greedy(self,beam=5,weight=0.0,power=1.0,alpha=0.,anchor=False,select=0,resource=False,prices=None,deadline=math.inf,debug=False):
  result=[]; evaluated=0
  weightgroups={}
  if resource:
   low=min(self.app.values())
   for i,m in enumerate(self.masks):
    w=(1+weight*(m.bit_count()-1))*self.cost(m,self.kinds[i],1)/low
    weightgroups[w]=weightgroups.get(w,0)|(1<<i)
  for ep,ii in sorted(self.epochs.items(),reverse=self.reverse):
   remain=ii[::-1] if self.reverse else ii[:]
   while remain:
    if time.monotonic()>deadline:
     result.extend(remain);break
    req={}; rk={}; grouped={}; gd={}; gp={}; gw={};gdw={};gpw={}
    a2=0; a3=0
    for i in remain:
     m=self.masks[i]; k=self.kinds[i]
     for p in self.parents[i]:
      m|=req.get(p,0); k|=rk.get(p,0)
     req[i]=m;rk[i]=k
     if m.bit_count()<=self.cap:
      grouped[m]=grouped.get(m,0)|(1<<i)
      if prices is not None:
       gw[m]=gw.get(m,0.)+prices[i]
       if k==2:gdw[m]=gdw.get(m,0.)+prices[i]
       if k==4:gpw[m]=gpw.get(m,0.)+prices[i]
      if k==2: gd[m]=gd.get(m,0)|(1<<i)
      if k==4: gp[m]=gp.get(m,0)|(1<<i)
      w=self.masks[i].bit_count()
      if w==2:a2|=1<<i
      elif w==3:a3|=1<<i
    seeds=list(grouped)
    cache={}; widths=[set() for _ in range(self.cap+1)]
    def evaluate(s):
     nonlocal evaluated
     old=cache.get(s)
     if old is not None:return old
     evaluated+=1
     bits=d=p=0; sub=s; vw=dw=pw=0.
     while sub:
      bits|=grouped.get(sub,0); d|=gd.get(sub,0);p|=gp.get(sub,0)
      if prices is not None:vw+=gw.get(sub,0.);dw+=gdw.get(sub,0.);pw+=gpw.get(sub,0.)
      sub=(sub-1)&s
     best=(math.inf,0)
     for b,k,pw0 in ((bits,1,vw),(d,2,dw),(p,4,pw)):
      if not b:continue
      count=b.bit_count(); c=min(self.limit,count)
      size=c*(1+weight*((b&a2).bit_count()+2*(b&a3).bit_count())/count)
      if resource:size=sum(w*(b&bg).bit_count() for w,bg in weightgroups.items())*c/count
      if prices is not None:size=pw0*c/count
      val=self.cost(s,k,c)*(1+alpha*s.bit_count())/(size**power)
      if val<best[0]:best=(val,b)
     cache[s]=best
     return best
    for s in seeds:widths[s.bit_count()].add(s);evaluate(s)
    for w in range(1,self.cap):
     top=sorted(widths[w],key=lambda s:evaluate(s)[0])[:beam]
     for a in top:
      for b in seeds:
       s=a|b; ws=s.bit_count()
       if w<ws<=self.cap:
        widths[ws].add(s)
    pool=[s for ss in widths for s in ss]
    if anchor:pool=[s for s in pool if evaluate(s)[1]>>remain[0]&1]
    best_s=min(pool,key=lambda s:evaluate(s)[0])
    b=cache[best_s][1]
    selected=[i for i in remain if b>>i&1]
    if len(selected)>self.limit and select:
     ancestors={}
     for i in selected:
      a=1<<i
      for pp in self.parents[i]:a|=ancestors.get(pp,0)
      ancestors[i]=a
     chosen=0;left=self.limit
     while left:
      top=None
      for i,aa in ancestors.items():
       a=aa&~chosen;n=a.bit_count()
       if not 0<n<=left:continue
       value=1+max(weight,1.)*((a&a2).bit_count()+2*(a&a3).bit_count())/n
       rank=(value,n,-i) if select==1 else (value,-n,-i)
       if top is None or rank>top[0]:top=rank,a
      if top is None:break
      chosen|=top[1];left=self.limit-chosen.bit_count()
     selected=[i for i in selected if chosen>>i&1]
    else:selected=selected[:self.limit]
    # Prefix subpartitioning is deferred to final order dynamic programming.
    selected_set=set(selected)
    remain=[i for i in remain if i not in selected_set]
    result.extend(selected)
  if self.reverse:result.reverse()
  if debug:print('evaluated',evaluated,file=sys.stderr)
  return self.partition(result)

def plan(case):
 win=partition(case,list(range(len(case['gates']))))
 for rev in (False,True):
  p=Problem(case,rev)
  for weight in (0.,1.):
   z=p.greedy(beam=5,weight=weight)
   if z[0]<win[0]:win=z
 base=baseline_plan(case)
 from model import validate_and_cost
 bc=validate_and_cost(case,base)
 if bc<win[0]:win=(bc,base)
 return win[1]

if __name__=='__main__':
 req=json.loads(Path(sys.argv[1]).read_text()); resp={'schedules':{c['id']:plan(c) for c in req['cases']}}
 Path(sys.argv[2]).write_text(json.dumps(resp))

#!/usr/bin/env python3
"""Structure-aware, costed state-vector fusion planner.

All transformations use the per-qubit dependency DAG.  Matrix construction
costs are included, including for blocks built by the local optimizers.
"""
import json
import math
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# The search uses processes, not threaded numerical kernels.
for _name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_name]='1'

from baseline import reordered
from fusion import Problem
from beam import BeamPlanner
from improve import improve
from pair_opt import PairOptimizer
from contract import Contractor
from model import validate_and_cost

class Portfolio:
    """Barriers make epoch-wise selection exact, without interactions."""
    def __init__(self,case,initial=None):
        self.case=case
        self.p=Problem(case)
        self.best={}
        self.cache={}
        if initial is not None:self.offer(initial)
    def offer(self,blocks):
        costs={};parts={}
        for b in blocks:
            ep=self.case['gates'][b[0]]['epoch']
            bits=sum(1<<i for i in b)
            cost=self.cache.get(bits)
            if cost is None:
                m=k=0
                for i in b:m|=self.p.masks[i];k|=self.p.kinds[i]
                cost=self.p.cost(m,k,len(b));self.cache[bits]=cost
            costs[ep]=costs.get(ep,0.)+cost
            parts.setdefault(ep,[]).append(b)
        changed=False
        for ep,co in costs.items():
            if ep not in self.best or co<self.best[ep][0]-1e-8:
                self.best[ep]=(co,parts[ep]);changed=True
        return changed
    def result(self):
        return [b for ep in sorted(self.best) for b in self.best[ep][1]]
    def cost(self):return sum(z[0] for z in self.best.values())

def baseline(case):
    po=Portfolio(case)
    po.offer(po.p.partition(list(range(len(case['gates']))))[1])
    for window in (1,3,6):
        for preference in ('dense','diagonal'):
            po.offer(po.p.partition(reordered(case,window,preference))[1])
    return po.result()

def reverse_problem(case,blocks):
    n=len(case['gates'])
    emap={ep:i for i,ep in enumerate(sorted({g['epoch'] for g in case['gates']},reverse=True))}
    rc=case.copy()
    rc['gates']=[dict(g,epoch=emap[g['epoch']]) for g in reversed(case['gates'])]
    rb=[[n-1-i for i in reversed(b)] for b in reversed(blocks)]
    return rc,rb

def _search(case,initial,budget,global_deadline):
    cpu_start=time.process_time()
    start=time.monotonic()
    po=Portfolio(case,initial)
    def remaining():return max(0.,min(budget-(time.process_time()-cpu_start),global_deadline-time.monotonic()))
    def limit(seconds):return time.monotonic()+max(0.,min(seconds,remaining()))
    def polish(seconds=.5):
        if remaining()>.02:
            z=improve(case,po.result(),passes=3,deadline=limit(seconds))
            po.offer(z[1])
    polish(.4)
    # Different arity weights balance narrow fusion, full operation-cap packing,
    # and leaving flexible one-qubit gates for subsequent blocks.
    configs=[(False,3.,0.,0,False),(True,3.,0.,0,False),(True,10.,0.,2,False),
             (False,0.,0.,0,False),(True,1.,.1,0,False),(False,1.,.3,0,False),
             (False,10.,0.,1,False),(True,0.,0.,0,False)]
    use_resource=(case['hardware']['stride_penalty']>0 and
                  case['hardware']['build']/case['repetitions']>.003)
    if use_resource:
        configs[2:2]=[(False,0.,0.,0,True),(False,3.,0.,0,True)]
    greedy_end=limit(min(5.8,budget*.27))
    for j,(rev,weight,alpha,selection,resource) in enumerate(configs):
        now=time.monotonic()
        if now>=greedy_end or remaining()<.08:break
        p=Problem(case,rev)
        dl=greedy_end
        if j<2:dl=min(dl,now+max(.4,(greedy_end-now)/2))
        z=p.greedy(beam=7 if selection else 5,weight=weight,alpha=alpha,
                   select=selection,resource=resource,deadline=dl)
        po.offer(z[1])
    polish(.5)
    if remaining()>1.:
        dl=limit(min(.8,remaining()*.06))
        z=Contractor(case,0.,0.,deadline=dl).run()
        po.offer(z[1]);polish(.3)
    # A bounded block-level beam retains alternate frontiers instead of
    # committing irrevocably to the best immediate cost per operation.
    for j,(rev,weight,cut,scale) in enumerate([(False,0.,True,1.),(True,0.,True,1.2),(False,0.,False,1.2)]):
        rem=remaining()
        if rem<.15:break
        slots=3-j
        allowance=max(.1,(rem-.6)/slots)
        cc=case;bb=po.result()
        if rev:cc,bb=reverse_problem(case,bb)
        width=32
        if cc['max_block_qubits']<=3:width=72
        bp=BeamPlanner(cc)
        z=bp.run(bb,beam=width,branch=16,weight=weight,cut=cut,scale=scale,resource=(use_resource and j==2),deadline=limit(allowance))
        if rev:
            n=len(case['gates'])
            z=(z[0],[[n-1-i for i in reversed(b)] for b in reversed(z[1])])
        po.offer(z[1]);polish(.3)
    if remaining()>.15:
        pp=PairOptimizer(case)
        z=pp.run(po.result(),passes=2,deadline=limit(min(.6,remaining()*.3)))
        po.offer(z[1])
        if remaining()>.15:
            z=pp.distant(po.result(),passes=1,deadline=limit(min(.7,remaining()*.4)))
            po.offer(z[1])
    # Spend spare time on a wider frontier beam, particularly useful for
    # highly parallel and diagonal-heavy circuits.
    if remaining()>.4:
        bp=BeamPlanner(case)
        z=bp.run(po.result(),beam=72,branch=20,weight=0.,cut=True,deadline=limit(remaining()-.2))
        po.offer(z[1])
    polish(.15)
    result=po.result()
    # Independent, public-model validation protects the baseline fallback.
    co=validate_and_cost(case,result)
    if co>validate_and_cost(case,initial)+1e-6:return initial
    return result

def _worker(payload):
    case,initial,budget,deadline=payload
    deadline=min(deadline,time.monotonic()+budget)
    try:return case['id'],_search(case,initial,budget,deadline)
    except Exception:
        # Never sacrifice validity when an optional search is interrupted or
        # encounters an unusual input structure.
        return case['id'],initial

def _refine_worker(payload):
    case,initial,budget,deadline=payload
    deadline=min(deadline,time.monotonic()+budget)
    try:
        po=Portfolio(case,initial)
        def left():return max(0.,deadline-time.monotonic())
        # Larger and differently scored frontiers diversify the first pass.
        for j,(rev,weight,scale,cut) in enumerate([(False,0.,1.15,False),(True,3.,1.,True)]):
            if left()<.2:break
            allocation=max(.05,(left()-.25)/(2-j))
            cc=case;bb=po.result()
            if rev:cc,bb=reverse_problem(case,bb)
            z=BeamPlanner(cc).run(bb,beam=72,branch=20,weight=weight,scale=scale,
                                 cut=cut,deadline=min(deadline,time.monotonic()+allocation))
            if rev:
                n=len(case['gates'])
                z=(z[0],[[n-1-i for i in reversed(b)] for b in reversed(z[1])])
            po.offer(z[1])
        if left()>.03:
            po.offer(improve(case,po.result(),passes=4,deadline=deadline)[1])
        out=po.result()
        if validate_and_cost(case,out)<=validate_and_cost(case,initial)+1e-6:
            return case['id'],out
    except Exception:
        pass
    return case['id'],initial

def plan(case,budget=22.):
    initial=baseline(case)
    return _search(case,initial,budget,time.monotonic()+budget+2.)

def main():
    request=json.loads(Path(sys.argv[1]).read_text())
    cases=request['cases']
    started=time.monotonic()
    schedules={c['id']:baseline(c) for c in cases}
    target=Path(sys.argv[2])
    # Checkpoint a complete legal batch before the optional optimization.
    target.write_text(json.dumps({'schedules':schedules},separators=(',',':')))
    if not cases:return
    workers=min(4,len(cases))
    deadline=started+166.
    budget=min(22.,max(.1,(deadline-time.monotonic()-3.)*workers/len(cases)*.91))
    # Long cases first keeps the four-worker tail short.
    jobs=sorted(cases,key=lambda c:len(c['gates']),reverse=True)
    if workers==1:
        cid,bs=_worker((jobs[0],schedules[jobs[0]['id']],budget,deadline))
        schedules[cid]=bs
        spare=deadline-time.monotonic()
        if spare>8.:
            cid,bs=_refine_worker((jobs[0],schedules[cid],min(14.,spare-2.),deadline))
            schedules[cid]=bs
    else:
        context=multiprocessing.get_context('fork')
        with ProcessPoolExecutor(max_workers=workers,mp_context=context) as pool:
            futures=[pool.submit(_worker,(c,schedules[c['id']],budget,deadline)) for c in jobs]
            for future in as_completed(futures):
                cid,bs=future.result();schedules[cid]=bs
            target.write_text(json.dumps({'schedules':schedules},separators=(',',':')))
            spare=deadline-time.monotonic()
            if spare>8.:
                extra=min(14.,spare*workers/len(jobs)*.82)
                futures=[pool.submit(_refine_worker,(c,schedules[c['id']],extra,deadline)) for c in jobs]
                for future in as_completed(futures):
                    cid,bs=future.result();schedules[cid]=bs
    target.write_text(json.dumps({'schedules':schedules},separators=(',',':')))

if __name__=='__main__':main()

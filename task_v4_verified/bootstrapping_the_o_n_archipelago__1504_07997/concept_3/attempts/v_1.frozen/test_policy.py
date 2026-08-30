import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys
import time
import json
import argparse
import policy
import numpy as np
try:
    import radial_public
except ModuleNotFoundError:
    sys.path.insert(0,os.environ['RADIAL_INPUT'])
from model import generate, Oracle, FAMILIES, SCALES, canonical_angle
from protocol import query, answer
from policy import Policy

def evaluate(seed,family,design=3,adaptive_tail=True):
    instance = generate(seed,family)
    oracle = Oracle(instance,seed+23487213)
    policy = Policy(initial_angles=design,adaptive_tail=adaptive_tail)
    started = time.monotonic()
    def measure(time,probe):
        query({'type':'measure','t':time,'u':probe})
        return oracle.measure(time,probe)['y']
    estimate,radii = policy.run(measure)
    answer({'type':'answer','estimate':dict(zip(__import__('policy').TARGETS,estimate.tolist())), 'radius90':dict(zip(__import__('policy').TARGETS,radii.tolist()))})
    assert oracle.used==72
    error = estimate-instance.target()
    error[3] = canonical_angle(error[3])
    absolute = np.abs(error)
    point = absolute/SCALES
    interval = (2*radii+20*np.maximum(absolute-radii,0))/(4*SCALES)
    combined = .7*point+.3*interval
    return dict(seed=seed,family=family,truth=instance.target().tolist(),estimate=estimate.tolist(),radii=radii.tolist(),error=error.tolist(),point=point.tolist(),loss=combined.tolist(),coverage=(absolute<=radii).tolist(),runtime=time.monotonic()-started,cost=policy.cost,parameters=policy.parameters.tolist(),design=[(float(__import__('policy').TIMES[index]),float(angle)) for index,angle,value in policy.records])

def summary(results):
    losses=[]
    report={'cases':len(results),'families':{},'max_runtime':max(result['runtime'] for result in results)}
    for family in FAMILIES:
        selected = [result for result in results if result['family']==family]
        if not selected:
            continue
        loss = np.mean([result['loss'] for result in selected])
        losses.append(loss)
        report['families'][family]={'cases':len(selected),'loss':float(loss),'point_loss':float(np.mean([result['point'] for result in selected])),'coverage90':float(np.mean([result['coverage'] for result in selected]))}
        print(family,len(selected),'loss',round(loss,5),'point',np.round(np.mean([result['point'] for result in selected],axis=0),4),'cover',np.round(np.mean([result['coverage'] for result in selected],axis=0),3),'seconds',round(np.mean([result['runtime'] for result in selected]),3),flush=True)
    print('ROBUST',.35*np.mean(losses)+.65*np.max(losses),flush=True)
    report['robust_loss']=float(.35*np.mean(losses)+.65*np.max(losses))
    report['worst_family_point_loss']=max(row['point_loss'] for row in report['families'].values())
    report['coverage90']=float(np.mean([result['coverage'] for result in results]))
    report['worst_family_coverage90']=min(row['coverage90'] for row in report['families'].values())
    print('SUMMARY',json.dumps(report),flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--count',type=int,default=10)
    parser.add_argument('--seed',type=int,default=1000)
    parser.add_argument('--family',default='all')
    parser.add_argument('--output',default='results.jsonl')
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--design',type=int,default=3)
    parser.add_argument('--fixed-tail',action='store_true')
    args=parser.parse_args()
    cases=[(args.seed+index,family,args.design,not args.fixed_tail) for index in range(args.count) for family in FAMILIES if args.family in ('all',family)]
    results=[]
    from concurrent.futures import ProcessPoolExecutor
    with open(args.output,'w') as output:
        if args.workers>1:
            executor=ProcessPoolExecutor(args.workers)
            futures=[executor.submit(evaluate,*case) for case in cases]
            iterator=(future.result() for future in futures)
        else:
            iterator=(evaluate(*case) for case in cases)
        for result in iterator:
            results.append(result)
            output.write(json.dumps(result)+'\n')
            output.flush()
            print(result['seed'],result['family'],round(np.mean(result['loss']),4),round(result['runtime'],2),flush=True)
    report=summary(results)
    with open(args.output+'.summary.json','w') as output:
        json.dump(report,output,indent=2)

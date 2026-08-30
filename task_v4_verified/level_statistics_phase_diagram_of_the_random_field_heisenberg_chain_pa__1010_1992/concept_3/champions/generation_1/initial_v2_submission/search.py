import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import time
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'participant/workspace'))
from exact import assess, family_fields, proxy_statistics, spectrum, validate_fields

ROOT = Path(__file__).resolve().parent
PROTOCOL = json.loads((ROOT.parents[1] / 'participant/input/protocol.json').read_text())
SCALES = np.array([1.0] + [family['scale'] for family in PROTOCOL['families'] for offset in family['offsets']])
OFFSETS = np.array([[0.0]*12] + [offset for family in PROTOCOL['families'] for offset in family['offsets']])

def evaluate(job):
    fields, indices = job
    results = []
    for index in indices:
        profile = SCALES[index] * np.array(fields) + OFFSETS[index]
        try:
            statistics = proxy_statistics(spectrum(profile))
            results.append(statistics['difference'])
        except ValueError:
            results.append(float('nan'))
    return results

def admissible(fields):
    try:
        validate_fields(fields)
    except ValueError:
        return False
    return True

def summarize(candidate):
    values = np.array(candidate['values']) * candidate['orientation']
    family_values = values[1:].reshape(4,8)
    means = family_values.mean(axis=1)
    coverage = (family_values >= .025).sum(axis=1)
    core = float(means.mean())
    worst = float(means.min())
    base = float(values[0])
    third = np.sort(family_values, axis=1)[:,2]
    score = .6*core + .4*worst - .5*max(0., .055-base) - .4*np.maximum(0., .025-third).mean()
    passed = core >= .060 and worst >= .050 and base >= .055 and bool(np.all(coverage>=6))
    return dict(core=core, worst=worst, base=base, means=means.tolist(), coverage=coverage.tolist(), score=score, passed=passed)

def generate(random, kind):
    if kind == 0:
        fields = random.uniform(-1,1,12)*random.uniform(1.2,7.0)
    elif kind == 1:
        fields = random.normal(size=12)*random.uniform(.7,3.5)
    elif kind == 2:
        fields = random.choice([-1.,1.],size=12)*random.uniform(1.,6.5)+random.normal(size=12)*random.uniform(.12,1.8)
    elif kind == 3:
        fields = (-1.)**np.arange(12)*random.uniform(.8,6.5)+random.normal(size=12)*random.uniform(.15,1.5)
    elif kind == 4:
        fields = random.normal(size=12)*random.uniform(.15,1.4)
        sites = random.choice(12,size=random.integers(1,4),replace=False)
        fields[sites] += random.choice([-1.,1.],size=len(sites))*random.uniform(4.,8.,size=len(sites))
    elif kind == 5:
        fields = np.arange(12)*random.uniform(.25,1.2)+random.normal(size=12)*random.uniform(.15,1.5)
        if random.random()<.5:
            random.shuffle(fields)
    elif kind == 6:
        count = int(random.integers(2,7))
        fields = np.repeat(np.arange(count), int(np.ceil(12/count)))[:12]*random.uniform(1.,4.)
        fields += random.normal(size=12)*random.uniform(.15,1.)
    elif kind == 7:
        fields = np.cos(2*np.pi*np.arange(12)*random.uniform(.05,.5)+random.uniform(0,2*np.pi))*random.uniform(1.,7.)
        fields += random.normal(size=12)*random.uniform(.15,.8)
    elif kind == 8:
        fields = np.tile(random.uniform(-4,4,6),2)+random.normal(size=12)*random.uniform(.15,.8)
    else:
        fields = random.normal(size=12)*random.uniform(.15,.8)
        fields[:6] += random.uniform(2.,7.)
        fields[6:] -= random.uniform(2.,7.)
    fields -= fields.mean()
    return fields

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=8271992)
    parser.add_argument('--seconds', type=float, default=2900)
    parser.add_argument('--batch', type=int, default=512)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--resume', action='store_true')
    arguments=parser.parse_args()
    random=np.random.default_rng(arguments.seed)
    started=time.monotonic()
    elites=[]
    if arguments.resume and (ROOT/'elites.json').exists():
        elites=json.loads((ROOT/'elites.json').read_text())
    evaluated=0
    round_number=0
    with concurrent.futures.ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        while time.monotonic()-started < arguments.seconds:
            round_number+=1
            candidates=[]
            while len(candidates)<arguments.batch:
                kind=int(random.integers(0,10))
                if elites and random.random()<.65:
                    parent=elites[int(random.integers(0,min(len(elites),12)))]
                    fields=np.array(parent['fields'])
                    amplitude=random.choice([.007,.02,.05,.1,.2,.4,.8])
                    if random.random()<.2:
                        fields*=1+random.normal()*amplitude*.5
                    else:
                        change=random.normal(size=12)*amplitude
                        if random.random()<.3:
                            change[random.random(12)<.7]=0
                        fields+=change
                    fields-=fields.mean()
                    kind=parent['kind']
                else:
                    fields=generate(random,kind)
                if admissible(fields):
                    candidates.append(dict(fields=fields.tolist(),kind=kind))
            results=list(executor.map(evaluate,[(candidate['fields'],[0]) for candidate in candidates]))
            evaluated+=len(candidates)
            for candidate,result in zip(candidates,results):
                candidate['values']=[result[0]]+[None]*32
                candidate['orientation']=1 if result[0]>=0 else -1
            candidates.sort(key=lambda candidate: abs(candidate['values'][0]), reverse=True)
            candidates=[candidate for candidate in candidates[:max(48,arguments.batch//8)] if abs(candidate['values'][0])>=.043]
            indices=[1,5,9,13,17,21,25,29]
            results=list(executor.map(evaluate,[(candidate['fields'],indices) for candidate in candidates]))
            evaluated+=len(candidates)*len(indices)
            for candidate,result in zip(candidates,results):
                for index,value in zip(indices,result):
                    candidate['values'][index]=value
                signed=np.array(result)*candidate['orientation']
                means=signed.reshape(4,2).mean(axis=1)
                candidate['screen_score']=.65*signed.mean()+.35*means.min()
            candidates.sort(key=lambda candidate:candidate['screen_score'],reverse=True)
            candidates=candidates[:16]
            remaining=[index for index in range(33) if index not in indices and index!=0]
            results=list(executor.map(evaluate,[(candidate['fields'],remaining) for candidate in candidates]))
            evaluated+=len(candidates)*len(remaining)
            for candidate,result in zip(candidates,results):
                for index,value in zip(remaining,result):
                    candidate['values'][index]=value
                candidate['summary']=summarize(candidate)
                elites.append(candidate)
            elites.sort(key=lambda candidate:candidate['summary']['score'],reverse=True)
            elites=elites[:40]
            (ROOT/'elites.json').write_text(json.dumps(elites,indent=2,allow_nan=False)+'\n')
            best=elites[0]
            witness={key:best[key] for key in ['fields','orientation']}
            witness['schema_version']=1
            (ROOT/'witness.json').write_text(json.dumps(witness,indent=2,allow_nan=False)+'\n')
            print(json.dumps(dict(round=round_number,seconds=round(time.monotonic()-started,1),spectra=evaluated,best=best['summary'],kind=best['kind'],top=[candidate['summary']['core'] for candidate in elites[:8]])),flush=True)
            for candidate in elites:
                if candidate['summary']['passed']:
                    witness={key:candidate[key] for key in ['fields','orientation']}
                    witness['schema_version']=1
                    try:
                        report=assess(witness,PROTOCOL)
                    except ValueError as error:
                        print('INVALID',error,flush=True)
                        continue
                    if report['pass']:
                        (ROOT/'witness.json').write_text(json.dumps(witness,indent=2,allow_nan=False)+'\n')
                        (ROOT/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
                        print('SUCCESS',json.dumps(candidate['summary']),flush=True)
                        return

if __name__=='__main__':
    main()

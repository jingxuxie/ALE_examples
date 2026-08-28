import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def evaluate(concept, phase, pool):
    directory = ROOT / concept
    attempt = directory / ('attempt' if phase == 'pilot' else f'attempt_{phase}')
    solver = attempt / 'solver.py'
    frozen = ROOT/'private'/'runs'/phase/'submissions'/f'{concept}.py'
    if frozen.exists():
        solver = frozen
    reports = ROOT / 'private' / 'scores' / phase
    reports.mkdir(parents=True,exist_ok=True)
    output = reports / f'{concept}_{pool}.json'
    if not solver.exists():
        result = dict(concept=concept,phase=phase,pool=pool,status='missing_submission',mean_core=None,worst_family=None)
        output.write_text(json.dumps(result,indent=2)+'\n')
        return result
    command = [sys.executable,str(directory/'private'/'evaluator.py'),'--submission',str(solver),
               '--pool',pool,'--output',str(output)]
    environment = dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    process = subprocess.run(command,capture_output=True,text=True,env=environment,timeout=7200)
    (reports/f'{concept}_{pool}.log').write_text(process.stdout+'\n'+process.stderr)
    if process.returncode:
        return dict(concept=concept,status='evaluator_failed',returncode=process.returncode,stderr=process.stderr[-2000:])
    result = json.loads(output.read_text())
    mean = next((result.get(key) for key in ['mean_core','mean_challenge','mean_selected','mean_score','mean']
                 if result.get(key) is not None),None)
    return dict(concept=concept,phase=phase,pool=pool,mean=mean,
                **{key:result.get(key) for key in ['worst_family','families']})


def locked_evaluate(concept, phase, pool, force=False):
    reports = ROOT/'private'/'scores'/phase
    reports.mkdir(parents=True,exist_ok=True)
    with (reports/f'{concept}_{pool}.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        output = reports/f'{concept}_{pool}.json'
        if output.exists() and not force:
            result = json.loads(output.read_text())
            if result.get('cases'):
                mean = next((result.get(key) for key in ['mean_core','mean_challenge','mean_selected','mean_score','mean']
                             if result.get(key) is not None),None)
                return dict(concept=concept,phase=phase,pool=pool,cached=True,mean=mean,
                            **{key:result.get(key) for key in ['worst_family','families']})
        return evaluate(concept,phase,pool)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('concepts',nargs='+')
    parser.add_argument('--phase',default='pilot')
    parser.add_argument('--pool',default='core',choices=['core','challenge'])
    parser.add_argument('--force',action='store_true')
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=len(args.concepts)) as executor:
        futures = [executor.submit(locked_evaluate,concept,args.phase,args.pool,args.force) for concept in args.concepts]
        for future in as_completed(futures):
            print(json.dumps(future.result()),flush=True)


if __name__ == '__main__':
    main()

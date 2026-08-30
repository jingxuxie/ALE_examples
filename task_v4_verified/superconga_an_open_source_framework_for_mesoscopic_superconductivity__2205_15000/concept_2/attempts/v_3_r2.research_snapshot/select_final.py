import os

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'

import json
from concurrent.futures import ProcessPoolExecutor

from optimize import OUTPUT,load_problem,ROOT,response,discrepancies,validate_design


def evaluate(path):
    try:
        config,target=load_problem(ROOT/'participant/input')
        pattern=json.loads(path.read_text())['pattern']
        validate_design(config,pattern)
        metrics=discrepancies(config,response(config,pattern),target)
        return str(path.name),metrics,pattern
    except (ValueError,KeyError,json.JSONDecodeError):
        return None


if __name__=='__main__':
    paths=list(OUTPUT.glob('*.json'))
    with ProcessPoolExecutor(max_workers=8) as executor:
        results=[result for result in executor.map(evaluate,paths) if result is not None]
    results.sort(key=lambda result:result[1]['relative_rmse'])
    for name,metrics,pattern in results[:12]:
        print(name,metrics,flush=True)
    name,metrics,pattern=results[0]
    destination=OUTPUT/'design.json'
    if destination.exists():
        os.chmod(destination,0o644)
    destination.write_text(json.dumps({'pattern':pattern},separators=(',',':'))+'\n')
    print('SELECTED',name,'bytes',destination.stat().st_size,'count',sum(pattern),'metrics',metrics,flush=True)

import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import concurrent.futures
import json
import time
from pathlib import Path
import numpy as np
from scipy.sparse.linalg import LinearOperator, eigsh, splu
from physics import ForwardModel, feasibility, geometry_arrays, load_result


def evaluate(request,masks,point,count,topology):
    started = time.monotonic()
    model = ForwardModel(request,masks,point)
    momenta = np.linspace(0,np.pi,count)
    gaps = []
    initial = np.random.RandomState(17).normal(size=model.dimension)
    for momentum in momenta:
        matrix = model.hamiltonian(float(momentum))
        factor = splu(matrix,permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.0)
        inverse = LinearOperator(matrix.shape,matvec=factor.solve,dtype=complex)
        energies,states = eigsh(matrix,k=8,sigma=0.0,which='LM',OPinv=inverse,
                               tol=2e-9,ncv=32,maxiter=1000,v0=initial)
        residual = np.max(np.linalg.norm(matrix@states-states*energies,axis=0))
        if not np.all(np.isfinite(energies)) or residual>2e-6:
            energies,_ = model.low_energy(float(momentum))
        gaps.append(float(np.min(np.abs(energies))))
    minimum = int(np.argmin(gaps))
    result = dict(gap_mev=gaps[minimum],momentum_rad=float(momenta[minimum]),
                  gaps_mev=gaps,momenta_rad=momenta.tolist())
    checks = {}
    for index in sorted(set((0,minimum,count-1))):
        reference = float(np.min(np.abs(model.low_energy(float(momenta[index]))[0])))
        if abs(reference-gaps[index])>2e-6:
            raise ArithmeticError('Independent eigensolver disagreement')
        checks[index] = reference
    result['authoritative_spot_checks_mev'] = checks
    if topology:
        result['invariant'] = model.topological_invariant()
    result['seconds'] = time.monotonic()-started
    result['scenario'] = point
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--geometry')
    parser.add_argument('--output',required=True)
    parser.add_argument('--momenta',type=int,default=51)
    parser.add_argument('--topology',action='store_true')
    arguments = parser.parse_args()
    request = json.loads(Path(arguments.input).read_text())
    masks = load_result(request,arguments.geometry) if arguments.geometry else geometry_arrays(request,request['baseline_geometry'])
    result = dict(feasibility=feasibility(request,masks))
    if result['feasibility']['valid']:
        with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(evaluate,request,masks,point,arguments.momenta,arguments.topology) for point in request['operating_points']]
            result['scenarios'] = []
            for future in jobs:
                scenario = future.result()
                result['scenarios'].append(scenario)
                print(json.dumps({key:value for key,value in scenario.items()
                                  if key not in ('gaps_mev','momenta_rad')}),flush=True)
        gaps = [scenario['gap_mev'] for scenario in result['scenarios']]
        result['robust_gap_mev'] = float(.5*np.mean(gaps)+.5*min(gaps))
    Path(arguments.output).write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({key:value for key,value in result.items() if key!='scenarios'}),flush=True)


if __name__=='__main__':
    main()

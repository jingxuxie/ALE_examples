import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'participant' / 'workspace'))
from physics import ForwardModel, feasibility, geometry_arrays, load_result


def measure(arguments):
    request, masks, scenario, count, name = arguments
    started = time.monotonic()
    model = ForwardModel(request, masks, scenario)
    result = model.spectral_gap(np.linspace(0, np.pi, count))
    result['class_d_invariant'] = model.topological_invariant()
    result['scenario'] = scenario
    result['geometry'] = name
    result['seconds'] = time.monotonic() - started
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--geometry', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--momenta', type=int, default=51)
    arguments = parser.parse_args()
    with open(arguments.input) as handle:
        request = json.load(handle)
    masks = load_result(request, arguments.geometry)
    valid = feasibility(request, masks)
    if not valid['valid']:
        raise ValueError(valid)
    baseline = geometry_arrays(request, request['baseline_geometry'])
    region = request['operating_region']
    scenarios = []
    for chemical, field in [(0.271, 0.743), (0.637, 0.213), (0.891, 0.564)]:
        scenarios.append(dict(mu_normal_mev=region['mu_normal_mev'][0] + chemical * np.ptp(region['mu_normal_mev']),
                              zeeman_mev=region['zeeman_mev'][0] + field * np.ptp(region['zeeman_mev'])))
    jobs = [(request, geometry, point, arguments.momenta, name)
            for point in scenarios for name, geometry in [('baseline', baseline), ('submission', masks)]]
    diagnostics = dict(feasibility=valid, measurements=[])
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        for result in pool.map(measure, jobs):
            diagnostics['measurements'].append(result)
            print(result['geometry'], result['scenario'], result['gap_mev'], result['class_d_invariant'], flush=True)
            with open(arguments.output, 'w') as handle:
                json.dump(diagnostics, handle, indent=2)
    for name in ['baseline', 'submission']:
        gaps = [result['gap_mev'] for result in diagnostics['measurements'] if result['geometry'] == name]
        diagnostics[name + '_robust_gap_mev'] = float(0.5 * np.mean(gaps) + 0.5 * np.min(gaps))
    with open(arguments.output, 'w') as handle:
        json.dump(diagnostics, handle, indent=2)


if __name__ == '__main__':
    main()

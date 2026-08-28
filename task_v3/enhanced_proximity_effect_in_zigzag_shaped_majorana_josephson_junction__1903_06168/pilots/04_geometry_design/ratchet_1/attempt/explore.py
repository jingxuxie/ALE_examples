import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import concurrent.futures
import json
import time
import numpy as np
from physics import ForwardModel, feasibility
from fast_physics import Spectrum
from geometry import make_geometry


def evaluate(parameters):
    started = time.monotonic()
    request = json.load(open('../participant/input/example.json'))
    masks = make_geometry(request, parameters)
    valid = feasibility(request, masks)
    result = dict(parameters=parameters, valid=valid['valid'])
    if not result['valid']:
        return result
    gaps = []
    try:
        for point in request['operating_points']:
            spectrum = Spectrum(ForwardModel(request, masks, point))
            invariant = spectrum.invariant(True)
            if invariant != -1:
                result['valid'] = False
                break
            gaps.append(min(spectrum.values.values()))
        result['gaps'] = gaps
        if len(gaps) == 3:
            result['merit'] = float(.5*np.mean(gaps)+.5*min(gaps))
    except Exception as error:
        result['error'] = str(error)
    result['seconds'] = time.monotonic()-started
    return result


if __name__ == '__main__':
    candidates = [None]
    for frequency, amplitudes in [(1,[150,220,300]), (2,[140,180,220,260,300]), (3,[80,120,160,200,240]), (4,[80,120,160])]:
        for amplitude in amplitudes:
            for width in [90,110,130,150]:
                candidates.append(dict(frequency=frequency, amplitude=amplitude, width=width))
    started = time.monotonic()
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(evaluate, parameters) for parameters in candidates]
        for future in concurrent.futures.as_completed(jobs):
            result = future.result()
            results.append(result)
            print(round(time.monotonic()-started,1), result, flush=True)
            with open('explore.json','w') as handle:
                json.dump(results,handle)

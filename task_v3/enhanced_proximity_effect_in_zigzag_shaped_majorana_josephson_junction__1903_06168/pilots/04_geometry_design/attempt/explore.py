from lab import *
from fast_physics import Spectrum
import concurrent.futures


def evaluate(arguments):
    request, parameters, scenarios, count = arguments
    masks = geometry_arrays(request, request['baseline_geometry']) if parameters is None else geometry(request, **parameters)
    feasible = feasibility(request, masks)
    if not feasible['valid']:
        return parameters, feasible, [], []
    gaps, invariants = [], []
    for scenario in scenarios:
        spectrum = Spectrum(ForwardModel(request, masks, scenario))
        invariants.append(spectrum.invariant(True))
        gaps.append(spectrum.scan(count))
    return parameters, feasible, gaps, invariants


def main():
    with open(Path(__file__).resolve().parent.parent / 'participant' / 'input' / 'example.json') as handle:
        request = json.load(handle)
    scenarios = [dict(mu_normal_mev=mu, zeeman_mev=zeeman) for mu,zeeman in [(11,0.7),(12.5,1),(14,1.3)]]
    candidates = [None] + [dict(amplitude=amplitude,width=width) for amplitude in [60,100,140,180,220] for width in [120,180,240,300]]
    candidates += [dict(amplitude=amplitude,width=width,kind='cosine') for amplitude in [100,160,220] for width in [160,240]]
    started=time.monotonic()
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        for result in pool.map(evaluate, [(request, candidate, scenarios, 5) for candidate in candidates]):
            parameters,feasible,gaps,invariants=result
            score=(0.5*np.mean(gaps)+0.5*np.min(gaps)) if gaps and max(invariants)<0 else 0
            results.append(dict(parameters=parameters,gaps=gaps,invariants=invariants,score=score,feasible=feasible))
            print(round(time.monotonic()-started,2),json.dumps(results[-1]),flush=True)
    with open(Path(__file__).resolve().parent/'explore.json','w') as handle:
        json.dump(results,handle,indent=2)


if __name__=='__main__':
    main()

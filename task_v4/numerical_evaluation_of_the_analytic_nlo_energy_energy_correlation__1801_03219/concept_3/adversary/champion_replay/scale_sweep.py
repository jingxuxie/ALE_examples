import concurrent.futures
import json
from pathlib import Path
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent


def correlation(values):
    values = np.asarray(values,dtype=np.int64)
    return np.asarray([int(values @ np.roll(values,-lag)) for lag in range(len(values))],dtype=np.int64)


def fixture(pair_count,seed):
    generator = np.random.default_rng(seed)
    ones,twos = pair_count//8,pair_count//16
    occupied = ones+twos
    extra = pair_count-2*occupied
    bars = np.sort(generator.choice(extra+occupied-1,size=occupied-1,replace=False))
    boundaries = np.r_[-1,bars,extra+occupied-1]
    gaps = np.diff(boundaries)+1
    weights = np.r_[np.ones(ones,dtype=int),np.full(twos,2,dtype=int)]
    generator.shuffle(weights)
    values = np.zeros(pair_count,dtype=np.int64)
    positions = (np.r_[0,np.cumsum(gaps[:-1])]+generator.integers(pair_count))%pair_count
    values[positions] = weights
    assert np.count_nonzero(values*np.roll(values,1)) == 0
    return correlation(values)


def replay(configuration):
    pair_count,case_seed,solver_seed,seconds,original = configuration
    if original:
        expected = np.asarray(json.loads((ROOT/"champions/generation_1/task_snapshot/participant/input/target.json").read_text())["cyclic_autocorrelation"],dtype=np.int64)
    else:
        expected = fixture(pair_count,case_seed)
    magnitudes = np.sqrt(np.maximum(np.fft.rfft(expected).real,0))
    generator = np.random.default_rng(solver_seed)
    values = generator.normal(0.25,0.55,pair_count)
    discrete = np.zeros(pair_count)
    twos,occupied,mass = pair_count//16,3*pair_count//16,pair_count//4
    started = time.monotonic()
    best_error,best_cost,iterations = float("inf"),None,0
    matched = 0
    while time.monotonic()-started < seconds:
        discrete.fill(0)
        ordering = np.argsort(values)[::-1]
        discrete[ordering[:twos]] = 2
        discrete[ordering[twos:occupied]] = 1
        spectrum = np.fft.rfft(2*discrete-values)
        spectrum *= magnitudes/np.maximum(np.abs(spectrum),1e-20)
        spectrum[0] = mass
        second = np.fft.irfft(spectrum,n=pair_count)
        difference = second-discrete
        values += 0.5*difference
        error = float(difference@difference)
        best_error = min(best_error,error)
        if error < 1e-10 or iterations%10000 == 0:
            approximate = np.rint(np.fft.irfft(np.abs(np.fft.rfft(discrete))**2,n=pair_count)).astype(np.int64)
            cost = int(np.sum((approximate-expected)**2))
            if best_cost is None or cost < best_cost:
                best_cost = cost
                matched = int(np.count_nonzero(approximate == expected))
            if cost == 0:
                exact = correlation(discrete.astype(int))
                assert np.array_equal(exact,expected)
                return {"pair_count":pair_count,"case_seed":case_seed,"solver_seed":solver_seed,"original":original,"passed":True,"iterations":iterations,"elapsed_seconds":time.monotonic()-started,"squared_error":0,"matched_lags":pair_count}
        iterations += 1
    return {"pair_count":pair_count,"case_seed":case_seed,"solver_seed":solver_seed,"original":original,"passed":False,"iterations":iterations,"elapsed_seconds":time.monotonic()-started,"squared_error":best_cost,"matched_lags":matched,"best_projection_residual":best_error}


def main():
    configurations = [(512,0,1,120,True)]
    configurations += [(size,20260828+index,1,90,False) for size in [512,1024,2048,4096] for index in range(4)]
    records = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for result in executor.map(replay,configurations,chunksize=1):
            records.append(result)
            print(json.dumps(result),flush=True)
            (OUTPUT/"scale_results.json").write_text(json.dumps({"algorithm":"fresh v1 relaxed-reflection Fourier/discrete projections, beta0.5; only dimensions/counts parameterized","case_seconds":90,"records":records,"complete":len(records)==len(configurations)},indent=2)+"\n")


if __name__ == "__main__":
    main()

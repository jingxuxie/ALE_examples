import argparse
import json
from pathlib import Path
import time

import numpy as np


def feasible_projection(vector,ones,twos):
    result = np.zeros(len(vector),dtype=np.int64)
    count = 0
    for index in np.argsort(vector)[::-1]:
        if result[(index-1)%len(vector)] or result[(index+1)%len(vector)]:
            continue
        result[index] = 2 if count < twos else 1
        count += 1
        if count == ones+twos:
            return result
    raise RuntimeError("spacing projection did not fill the requested counts")


def solve(expected,ones,twos,seconds,seed,beta):
    size = len(expected)
    mass = ones+2*twos
    magnitudes = np.sqrt(np.maximum(np.fft.rfft(expected).real,0))
    values = np.random.default_rng(seed).normal(mass/size,0.55,size)
    discrete = np.zeros(size)
    started = time.monotonic()
    best_residual = float("inf")
    best_values = values.copy()
    iterations = 0
    while time.monotonic()-started < seconds:
        discrete.fill(0)
        ordering = np.argsort(values)[::-1]
        discrete[ordering[:twos]] = 2
        discrete[ordering[twos:twos+ones]] = 1
        spectrum = np.fft.rfft(2*discrete-values)
        spectrum *= magnitudes/np.maximum(np.abs(spectrum),1e-20)
        spectrum[0] = mass
        second = np.fft.irfft(spectrum,n=size)
        difference = second-discrete
        values += beta*difference
        residual = float(difference@difference)
        if residual < best_residual:
            best_residual = residual
            best_values = values.copy()
        if residual < 1e-10:
            candidate = discrete.astype(np.int64)
            actual = np.rint(np.fft.irfft(np.abs(np.fft.rfft(candidate))**2,n=size)).astype(np.int64)
            if np.array_equal(actual,expected) and not np.any(candidate*np.roll(candidate,1)):
                return candidate,{"iterations":iterations,"elapsed_seconds":time.monotonic()-started,"exact_fft_check":True,"best_projection_residual":best_residual}
        iterations += 1
    return feasible_projection(best_values,ones,twos),{"iterations":iterations,"elapsed_seconds":time.monotonic()-started,"exact_fft_check":False,"best_projection_residual":best_residual}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    parser.add_argument("--target",type=Path,default=Path(__file__).resolve().parents[1]/"input/target.json")
    parser.add_argument("--seconds",type=float,default=120)
    parser.add_argument("--seed",type=int,default=1)
    parser.add_argument("--beta",type=float,default=0.5)
    arguments = parser.parse_args()
    target = json.loads(arguments.target.read_text())
    expected = np.asarray(target["cyclic_autocorrelation"],dtype=np.int64)
    counts = target.get("counts",{})
    ones,twos = int(counts.get("1",len(expected)//8)),int(counts.get("2",len(expected)//16))
    candidate,report = solve(expected,ones,twos,arguments.seconds,arguments.seed,arguments.beta)
    arguments.output.mkdir(parents=True,exist_ok=True)
    (arguments.output/"design.json").write_text(json.dumps({"schema_version":1,"a":candidate.tolist()})+"\n")
    (arguments.output/"search_report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()

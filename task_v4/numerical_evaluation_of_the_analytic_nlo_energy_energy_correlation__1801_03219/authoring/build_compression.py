import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
import time

import mpmath as mp
import numpy as np
from numpy.polynomial import chebyshev
from scipy.fft import dct

import native_kernel


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
sys.path.insert(0, str(CONCEPT / "participant" / "workspace"))
from model import bin_average, evaluate


def native_value(coordinate):
    with mp.workdps(110):
        coordinate = mp.mpf(float(coordinate))
        angular = 1/(1+mp.exp(-coordinate))
        channels = native_kernel._components(angular)
        return [float(mp.re(angular*(1-angular)*value)) for value in channels]


def native_derivative(coordinate):
    with mp.workdps(140):
        displacement = mp.mpf("1e-35")
        argument = mp.mpf(float(coordinate)) + mp.j * displacement
        angular = 1/(1+mp.exp(-argument))
        channels = native_kernel._components(angular)
        return [float(mp.im(angular*(1-angular)*value)/displacement) for value in channels]


def make_reference(degree, executor):
    knots = np.linspace(-24, 24, 25)
    canonical = np.cos(np.arange(degree+1)*np.pi/degree)
    coordinates = np.concatenate([left+(right-left)*(canonical+1)/2
                                   for left, right in zip(knots[:-1], knots[1:])])
    values = list(executor.map(native_value, coordinates, chunksize=8))
    blocks = np.asarray(values).reshape(24, degree+1, 3)
    coefficients = []
    for block in blocks:
        channels = dct(block, type=1, axis=0) / degree
        channels[[0, -1]] /= 2
        coefficients.append(channels.T)
    return {"knots": knots, "coefficients": np.asarray(coefficients)}


def main():
    started = time.monotonic()
    for relative in ["participant/input", "evaluator/hidden", "attempts", "champions", "adversary"]:
        (CONCEPT / relative).mkdir(parents=True, exist_ok=True)
    high_path = CONCEPT / "evaluator" / "hidden" / "oracle.npz"
    low_path = CONCEPT / "evaluator" / "hidden" / "oracle_low.npz"
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        if high_path.exists() and low_path.exists():
            high = dict(np.load(high_path))
            low = dict(np.load(low_path))
        else:
            print("Generating independent degree-40 and degree-24 native interpolants", flush=True)
            high = make_reference(40, executor)
            low = make_reference(24, executor)
            np.savez(high_path, **high)
            np.savez(low_path, **low)
        generator = np.random.default_rng(180103219)
        validation_coordinates = generator.uniform(-24, 24, 96)
        direct_values = np.asarray(list(executor.map(native_value, validation_coordinates)))
        direct_derivatives = np.asarray(list(executor.map(native_derivative, validation_coordinates)))
    coordinates = np.linspace(-24, 24, 10001)
    comparisons = {}
    for label, derivative in [("values", False), ("derivatives", True)]:
        truth = evaluate(high, coordinates, derivative)
        discrepancy = np.abs(evaluate(low, coordinates, derivative)-truth)/(1+np.abs(truth))
        comparisons["degree_24_40_"+label] = float(np.max(discrepancy))
    for label, truth, derivative in [("native_values", direct_values, False),
                                      ("complex_step_derivatives", direct_derivatives, True)]:
        comparisons[label] = float(np.max(np.abs(evaluate(high, validation_coordinates, derivative)-truth)/(1+np.abs(truth))))
    if max(comparisons.values()) > 2e-9:
        raise ValueError(f"oracle convergence failed: {comparisons}")
    calibration_coordinates = np.linspace(-24, 24, 769)
    np.savez(CONCEPT / "participant" / "input" / "calibration.npz",
             coordinates=calibration_coordinates,
             values=evaluate(high, calibration_coordinates),
             derivatives=evaluate(high, calibration_coordinates, True))
    test_coordinates = np.sort(np.concatenate([
        generator.uniform(-24, -10, 160), generator.uniform(-10, -3, 160),
        generator.uniform(-3, 3, 160), generator.uniform(3, 10, 160),
        generator.uniform(10, 24, 160), [-24, 24],
    ]))
    lower = generator.uniform(-23.9, 23.9, 300)
    widths = np.exp(generator.uniform(np.log(1e-5), np.log(12), 300))
    upper = np.minimum(24, lower+widths)
    bins = np.column_stack((lower, upper))
    averages = np.array([bin_average(high, left, right) for left, right in bins])
    low_averages = np.array([bin_average(low, left, right) for left, right in bins])
    comparisons["bin_averages_degree_24_40"] = float(np.max(np.abs(averages-low_averages)/(1+np.abs(averages))))
    weights = generator.normal(size=(len(test_coordinates), 3))
    weights /= np.sum(np.abs(weights), axis=1)[:, None]
    combination_values = evaluate(high, test_coordinates)
    for index in range(0, len(test_coordinates), 3):
        orthogonal = np.array([combination_values[index, 1], -combination_values[index, 0], 0.0])
        weights[index] = orthogonal / np.sum(np.abs(orthogonal))
    np.savez(CONCEPT / "evaluator" / "hidden" / "cases.npz",
             coordinates=test_coordinates, values=evaluate(high, test_coordinates),
             derivatives=evaluate(high, test_coordinates, True),
             bins=bins, averages=averages, weights=weights)
    (CONCEPT / "evaluator" / "hidden" / "oracle_audit.json").write_text(json.dumps({
        "native_decimal_precision": 110, "derivative_decimal_precision": 140,
        "derivative_complex_step": "1e-35", "direct_validation_points": 96,
        "dense_convergence_points": 10001, "independent_panel_degrees": [24,40],
        "mixed_discrepancies": comparisons, "elapsed_seconds": time.monotonic()-started,
        "source_sha256": hashlib.sha256(Path(native_kernel.__file__).read_bytes()).hexdigest(),
    }, indent=2)+"\n")
    print(json.dumps(comparisons, indent=2), flush=True)


if __name__ == "__main__":
    main()

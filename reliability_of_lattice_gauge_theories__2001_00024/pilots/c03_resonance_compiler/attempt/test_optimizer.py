"""Compare the bounded native optimizer to exhaustive small DAC grids."""

import ctypes
import itertools
import os

import numpy as np

import solver


def main():
    generator = np.random.default_rng(72913)
    library = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "optimizer.so"))
    function = library.optimize_schedule
    int_pointer = ctypes.POINTER(ctypes.c_int)
    double_pointer = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [ctypes.c_int, ctypes.c_int, int_pointer, int_pointer, int_pointer,
                         double_pointer, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_int, ctypes.c_double, ctypes.c_uint, int_pointer]
    function.restype = ctypes.c_double
    exact = 0
    for index in range(30):
        length = 4 if index % 2 else 6
        caps = np.full(length, 2, dtype=np.int32)
        uncertainty = generator.uniform(0, 0.01, size=length)
        rows = np.zeros((length * 2, length), dtype=np.int32)
        for row_index in range(len(rows)):
            sites = generator.choice(length, size=int(generator.integers(1, 4)), replace=False)
            rows[row_index, sites] = generator.choice([-2, -1, 1, 2], size=len(sites))
        positive = np.zeros(length, dtype=np.int32)
        hardware = {"denominator": 3, "bandwidth": 2, "caps": caps,
                    "uncertainty": uncertainty, "phase_denominator": 4}
        phase = 0 if index % 3 else 7
        ticks = np.zeros(length, dtype=np.int32)
        native = function(length, len(rows), rows.ctypes.data_as(int_pointer), caps.ctypes.data_as(int_pointer),
                          positive.ctypes.data_as(int_pointer), uncertainty.ctypes.data_as(double_pointer),
                          3, 2, phase, 4, 0.15, index + 83, ticks.ctypes.data_as(int_pointer))
        actual = solver._quality(solver.margins(rows, ticks, hardware, phase or None))
        assert abs(native - actual) < 1e-12, (index, native, actual)
        candidates = np.array(list(itertools.product(range(-2, 3), repeat=length)))
        gaps = candidates @ rows.T / 3
        errors = np.abs(rows) @ uncertainty
        if phase:
            values = np.maximum(0, np.abs((phase / 4 * gaps + 1) % 2 - 1) - phase / 4 * errors)
        else:
            values = np.maximum(0, np.abs(gaps) - errors) / 2
        optimum = np.max(0.75 * values.min(axis=1) + 0.25 * values.mean(axis=1))
        assert actual <= optimum + 1e-12
        exact += actual >= optimum - 1e-10
        print(index, "score", round(actual, 8), "optimum", round(optimum, 8), flush=True)
    print("Exact global optima:", exact, "/", 30)


if __name__ == "__main__":
    main()

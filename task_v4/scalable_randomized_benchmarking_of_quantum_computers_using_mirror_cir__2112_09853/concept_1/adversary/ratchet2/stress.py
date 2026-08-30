import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy

from model import GeneralModel


def compact(metrics):
    return {key: value for key, value in metrics.items() if key != "polarizations"}


def main():
    started = time.perf_counter()
    champion_path = Path(sys.argv[1]).resolve()
    champion_bytes = champion_path.read_bytes()
    champion = json.loads(champion_bytes)
    model = GeneralModel()
    counts = model.decode(champion)
    conditional = counts / 60
    baseline = model.uniform
    nominal = model.run(conditional, scan=True)
    nominal_baseline = model.run(baseline, scan=True)
    sampler_sweep = []
    for eta in (0.2, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8):
        observed = model.run(conditional, eta=eta, scan=True)
        control = model.run(baseline, eta=eta, scan=True)
        sampler_sweep.append({"champion": compact(observed), "baseline": compact(control),
                              "S2_difference": observed["polarizations"][1] - control["polarizations"][1]})
    rate_sweep = []
    for epsilon in (0.005, 0.01, 0.015, 0.018, 0.02, 0.022, 0.025, 0.03, 0.04):
        for scaled in (False, True):
            maximum = round(128 * 0.02 / epsilon) if scaled else 128
            observed = model.run(conditional, epsilon=epsilon, half_depth=maximum, scan=True)
            control = model.run(baseline, epsilon=epsilon, half_depth=maximum, scan=True)
            rate_sweep.append({"scaled_depth_horizon": scaled, "champion": compact(observed), "baseline": compact(control)})
    windows = [compact(model.run(conditional, lower_depth=lower, upper_depth=upper, scan=True))
               for lower, upper in ((0, 16), (0, 32), (0, 64), (0, 128), (0, 256), (16, 256), (32, 256), (64, 256))]
    short_depths = [{"depth": depth, "champion": nominal["polarizations"][depth // 2],
                     "baseline": nominal_baseline["polarizations"][depth // 2],
                     "difference": nominal["polarizations"][depth // 2] - nominal_baseline["polarizations"][depth // 2]}
                    for depth in (0, 2, 4, 6, 8, 12, 16, 24, 32, 64, 128, 256)]
    result = {"champion_path": str(champion_path), "champion_sha256": hashlib.sha256(champion_bytes).hexdigest(),
              "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
              "elapsed_seconds": time.perf_counter() - started, "nominal": compact(nominal),
              "nominal_baseline": compact(nominal_baseline), "family_calibrations": model.family_calibrations(counts),
              "sampler_sweep": sampler_sweep, "rate_sweep": rate_sweep,
              "fit_windows": windows, "short_depth_comparison": short_depths}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

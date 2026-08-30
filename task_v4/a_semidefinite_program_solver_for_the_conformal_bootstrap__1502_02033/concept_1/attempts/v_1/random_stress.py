import json
from pathlib import Path

import numpy as np

from benchmark import run


def cases():
    generator = np.random.default_rng(17881)
    for case_index in range(32):
        degree = int(generator.choice([2, 4, 8, 16, 24, 36, 48]))
        count = int(generator.integers(2, 7))
        family = case_index % 4
        damping = float(np.exp(generator.uniform(np.log(0.03), np.log(3.0))))
        pole_count = int(generator.integers(0, 25))
        centers = np.exp(generator.uniform(np.log(1e-5), np.log(1000.0), 4))
        labels = generator.integers(0, 4, pole_count)
        nominal = centers[labels]
        scenarios = []
        for scenario_index in range(count):
            current_damping = float(np.clip(damping * np.exp(generator.uniform(-0.5, 0.5)), 0.02, 5.0))
            if family == 0:
                poles = nominal
            elif family == 1:
                poles = nominal * np.exp(generator.uniform(-1.0, 1.0))
            elif family == 2:
                poles = nominal * np.exp(generator.uniform(-0.7, 0.7, pole_count))
            else:
                current_count = int(generator.integers(0, 25))
                poles = centers[generator.integers(0, 4, current_count)] * np.exp(generator.uniform(-0.5, 0.5))
            scenarios.append({"a": current_damping, "poles": np.clip(poles, 1e-6, 10000.0).tolist()})
        yield "random_" + str(case_index), {"degree": degree, "scenarios": scenarios}


if __name__ == "__main__":
    for name, data in cases():
        result = run(data, name)
        Path(name + ".json").write_text(json.dumps(result))

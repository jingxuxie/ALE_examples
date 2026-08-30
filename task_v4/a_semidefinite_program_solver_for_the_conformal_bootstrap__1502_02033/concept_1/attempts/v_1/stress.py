import json
from pathlib import Path
import sys

import numpy as np

from benchmark import ASSETS, run


def cases():
    for family in ("damping", "model", "near_origin", "separated"):
        original = json.loads((ASSETS / "input" / (family + ".json")).read_text())
        for degree in (2, 24, 48):
            yield family + "_" + str(degree), dict(original, degree=degree)
    for degree in (2, 12, 48):
        yield "empty_wide_" + str(degree), {"degree": degree, "scenarios": [{"a": 0.02, "poles": []}, {"a": 5.0, "poles": []}]}
        yield "pole_count_" + str(degree), {"degree": degree, "scenarios": [{"a": 1.0, "poles": []}, {"a": 1.0, "poles": [1e-6] * 24}]}
        yield "clusters_" + str(degree), {"degree": degree, "scenarios": [{"a": 0.5, "poles": [1e-6] * 8 + [0.1] * 8 + [1000.0] * 8}, {"a": 0.7, "poles": [2e-6] * 6 + [0.3] * 10 + [100.0] * 4}]}


if __name__ == "__main__":
    for name, data in cases():
        if len(sys.argv) > 1 and not any(part in name for part in sys.argv[1:]):
            continue
        result = run(data, name)
        Path("stress_" + name + ".json").write_text(json.dumps(result))

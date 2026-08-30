import json
from pathlib import Path

from benchmark import run


def cases():
    for degree in (2, 24, 48):
        yield "identical_empty_" + str(degree), {"degree": degree, "scenarios": [{"a": 1.0, "poles": []}] * 6}
        yield "identical_tiny_" + str(degree), {"degree": degree, "scenarios": [{"a": 0.02, "poles": [1e-6] * 24}] * 6}
        yield "tiny_damping_" + str(degree), {"degree": degree, "scenarios": [{"a": damping, "poles": [1e-6] * 24} for damping in (0.02, 0.1, 0.5, 1.0, 2.0, 5.0)]}
        yield "six_counts_" + str(degree), {"degree": degree, "scenarios": [{"a": damping, "poles": [1e-6] * count} for damping, count in zip((0.02, 0.1, 0.5, 1.0, 2.0, 5.0), (0, 3, 8, 12, 18, 24))]}
        yield "reverse_counts_" + str(degree), {"degree": degree, "scenarios": [{"a": damping, "poles": [1e-6] * count} for damping, count in zip((5.0, 2.0, 1.0, 0.5, 0.1, 0.02), (0, 3, 8, 12, 18, 24))]}
        yield "large_poles_" + str(degree), {"degree": degree, "scenarios": [{"a": damping, "poles": [10000.0] * 24} for damping in (0.02, 0.1, 0.5, 1.0, 2.0, 5.0)]}


if __name__ == "__main__":
    for name, data in cases():
        result = run(data, name)
        Path("edge_" + name + ".json").write_text(json.dumps(result))

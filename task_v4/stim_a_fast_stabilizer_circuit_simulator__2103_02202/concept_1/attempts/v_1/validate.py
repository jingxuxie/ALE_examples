import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import warnings

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import numpy as np
from scipy.optimize import linprog
from solve import compress_instance, improve_tables, marginals, serialize

warnings.filterwarnings("ignore", message="Unknown solver options.*")
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent.parent / "participant"
random.seed(17713)
generator = np.random.default_rng(8832)


def main():
    for source in (ASSETS / "input").glob("*.json"):
        instance = json.loads(source.read_text())
        compressed = compress_instance(instance)
        for trial in range(20):
            selected = sorted(random.sample(range(len(instance["taps"])), instance["budget"]))
            assert np.max(np.abs(marginals(instance, selected) - marginals(compressed, selected))) < 1e-13
        process = subprocess.run([str(ROOT / "engine"), "0.3"], input=serialize(compressed),
                                 text=True, stdout=subprocess.PIPE, check=True)
        candidates = json.loads(process.stdout)
        for answer in candidates:
            distribution = marginals(instance, answer["selected"])
            table = np.array(answer["correction"])
            score = distribution[:, np.arange(len(table)), 1 - table].sum(axis=1).max()
            assert abs(score - answer["score"]) < 1e-12
        print("Fourier and compression:", source.name, "passed", flush=True)
    for trial in range(8):
        detectors = 16 + (trial * 5) % 13
        regimes = 3 + trial % 4
        budget = 5 + trial % 3
        taps = set()
        while len(taps) < 28 + 2 * trial:
            taps.add(random.randrange(1, 1 << detectors))
        channels = []
        for channel_index in range(12 + trial):
            branches = 1 + channel_index % 3
            probabilities = generator.dirichlet(np.full(branches + 1, 0.6), size=regimes)[:, :-1]
            channels.append({"signatures": [random.randrange(1, 1 << (detectors + 1))
                                            for branch in range(branches)],
                             "probabilities": probabilities.tolist()})
        instance = {"detectors": detectors, "regimes": list(range(regimes)),
                    "budget": budget, "taps": sorted(taps), "channels": channels}
        compressed = compress_instance(instance)
        selected = sorted(random.sample(range(len(taps)), budget))
        assert np.max(np.abs(marginals(instance, selected) - marginals(compressed, selected))) < 1e-13
        process = subprocess.run([str(ROOT / "engine"), "0.1"], input=serialize(compressed),
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        for answer in json.loads(process.stdout)[:12]:
            distribution = marginals(instance, answer["selected"])
            table = np.array(answer["correction"])
            score = distribution[:, np.arange(len(table)), 1 - table].sum(axis=1).max()
            assert abs(score - answer["score"]) < 1e-12
    print("High-probability categorical channels: 8 cases passed", flush=True)
    for trial in range(40):
        regimes = 3 + trial % 4
        size = 8 + trial % 5
        distribution = generator.random((regimes, size, 2))
        distribution /= distribution.sum(axis=(1, 2))[:, None, None]
        difference = distribution[:, :, 0] - distribution[:, :, 1]
        base = distribution[:, :, 1].sum(axis=1)
        objective = np.r_[np.zeros(size), 1.0]
        relaxation = linprog(objective, A_ub=np.c_[difference, -np.ones(regimes)],
                             b_ub=-base, bounds=[(0, 1)] * (size + 1), method="highs")
        weights = np.maximum(-relaxation.ineqlin.marginals, 0)
        weights /= weights.sum()
        initial = (difference.mean(axis=0) < 0).astype(int)
        rows = ["1", f"{regimes} {size}", " ".join(map(str, base))]
        rows.extend(" ".join(map(str, column)) for column in difference.T)
        rows += [" ".join(map(str, weights)), " ".join(map(str, initial))]
        process = subprocess.run([str(ROOT / "engine"), "tables", "0.5"],
                                 input="\n".join(rows) + "\n", text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        answer = json.loads(process.stdout)
        assignments = (np.arange(1 << size)[:, None] >> np.arange(size)) & 1
        scores = np.max(base[:, None] + difference @ assignments.T, axis=0)
        actual = np.max(base + difference @ np.array(answer["correction"]))
        assert abs(actual - scores.min()) < 1e-12, (trial, actual, scores.min())
    print("Exact table optimizer: 40 exhaustive comparisons passed", flush=True)
    instance = {"detectors": 16, "regimes": ["zero", "one", "mixed"], "budget": 5,
                "taps": list(range(1, 29)),
                "channels": [{"signatures": [1 << 16], "probabilities": [[0], [1], [0.5]]}]}
    instance["channels"] += [{"signatures": [1 << 16], "probabilities": [[0], [0], [0]]}
                             for channel in range(11)]
    process = subprocess.run([str(ROOT / "engine"), "0.1"], input=serialize(compress_instance(instance)),
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    candidates = json.loads(process.stdout)
    assert all(len(candidate["correction"]) == 1 << len(candidate["selected"]) for candidate in candidates)
    answer = improve_tables(instance, candidates[:1], time.monotonic() + 2)
    assert len(answer["correction"]) == 1 << len(answer["selected"])
    distribution = marginals(instance, answer["selected"])
    table = np.array(answer["correction"])
    assert distribution[:, np.arange(len(table)), 1 - table].sum(axis=1).max() == 1
    print("Conflicting deterministic regimes: passed", flush=True)


if __name__ == "__main__":
    main()

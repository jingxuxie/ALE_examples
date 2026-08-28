"""Generate reproducible resource-test cases without private inputs."""

import copy
import json
from pathlib import Path
import resource
import sys
import time

import solve


def main():
    root = Path(__file__).resolve().parent
    with open(root.parent/"participant"/"input"/"example.json") as source:
        case = json.load(source)
    mode = sys.argv[1] if len(sys.argv) > 1 else "large"
    case.update(shape=[36, 36, 36], nfft=2048, steps=512,
                sample_steps=[0, 64, 256, 512], thermostat="quantum")
    if mode == "stiff":
        case["materials"][0].update(mu=0.4, K=0.5, omega0=180, Gamma=45, A=81000, T=0.15)
        partner = copy.deepcopy(case["materials"][0])
        partner.update(mu=2.5, omega0=90, Gamma=10, A=16200,
                       initial_direction=[-0.8, -0.3, -0.5])
        case["materials"].append(partner)
        case["exchange"] = [[2.0, -6.0], [-6.0, 0.5]]
    elif mode == "long_record":
        case.update(steps=2040, nfft=256, sample_steps=[0, 512, 2040])
        case["materials"][0].update(omega0=12, Gamma=4, A=250, T=0.1)
    limit = 1536*1024**2
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    started = time.perf_counter()
    memory_limit = 8*1024**2 if mode == "long_record" else 320*1024**2
    result = solve.solve(case, root, noise_memory_limit=memory_limit)
    print(mode, "elapsed", time.perf_counter()-started,
          "rss_kib", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          "shapes", {key: value.shape for key, value in result.items()})


if __name__ == "__main__":
    main()

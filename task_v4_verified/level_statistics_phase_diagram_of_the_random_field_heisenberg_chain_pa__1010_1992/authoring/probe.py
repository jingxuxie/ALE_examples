import json
import time
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from physics import observables


def main():
    results = []
    generator = np.random.default_rng(170823)
    with threadpool_limits(1):
        for length in (8, 10, 12):
            for scale in (1.5, 3.0, 5.0):
                fields = generator.uniform(-scale, scale, length)
                for kind, profile in (("random", fields), ("sorted", np.sort(fields))):
                    started = time.monotonic()
                    result = observables(profile)
                    result.update(length=length, scale=scale, kind=kind,
                                  seconds=time.monotonic() - started)
                    print(json.dumps(result), flush=True)
                    results.append(result)
    Path(__file__).with_name("probe.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

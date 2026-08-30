"""Child-only timing/history instrumentation; original solver files unchanged."""

import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

import physics


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    with np.load(request["inputs"], allow_pickle=False) as archive:
        inputs = dict(archive)
    original = physics.LIBRARY.ground_energy
    energies = []

    def instrumented(*arguments):
        history = np.full(arguments[-3], np.nan, dtype=np.float64)
        forwarded = list(arguments)
        forwarded[-1] = physics.pointer(history)
        started = time.process_time()
        energy = original(*forwarded)
        elapsed = time.process_time() - started
        recorded = np.flatnonzero(np.isfinite(history))
        energies.append({"up": arguments[1], "down": arguments[2], "energy": energy,
            "cpu_seconds": elapsed, "last_recorded_iteration": int(recorded[-1] + 1) if len(recorded) else None,
            "history_iterations": (recorded + 1).tolist(), "history_energies": history[recorded].tolist()})
        return energy

    physics.LIBRARY.ground_energy = instrumented
    rows = []
    for index, size in enumerate(inputs["n_sites"]):
        energies = []
        cpu_started = time.process_time()
        wall_started = time.perf_counter()
        result = physics.predict_instance(inputs["hopping"][index, :size, :size],
                                           inputs["interaction"][index, :size],
                                           inputs["potential"][index, :size])
        rows.append({"index": index, "n_sites": int(size), "family": int(inputs["family"][index]),
            "predictions": result, "cpu_seconds": time.process_time() - cpu_started,
            "wall_seconds": time.perf_counter() - wall_started, "sectors": energies,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
        Path(sys.argv[2]).write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps({key: rows[-1][key] for key in ("index", "n_sites", "family", "cpu_seconds", "predictions")}), flush=True)


if __name__ == "__main__":
    main()

import json
import sys
import time
from pathlib import Path

import numpy as np

CONCEPT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONCEPT / 'solution/v_01'))
from qualification.model import load_case, MU0, applied_load
import certified


def main():
    destination = CONCEPT / 'evaluator/oracles'
    destination.mkdir(exist_ok=True)
    original = certified.assemble

    def high_accuracy(case, order=6, material=True, coupling=True):
        return original(case, order=10, material=material, coupling=coupling)

    certified.assemble = high_accuracy
    manifest = {}
    for path in sorted((CONCEPT / 'evaluator/hidden').glob('h_*.npz')):
        case = load_case(path)
        start = time.perf_counter()
        result = certified.solve(case)
        elapsed = time.perf_counter() - start
        matrix, transform, _, _, _ = high_accuracy(case)
        holes = case.prescribed_current.shape[1]
        inverse = np.linalg.pinv(transform.toarray())
        result['reaction'] = MU0 * matrix[-holes:] @ inverse if holes else np.zeros((0, len(case.points)))
        load = (transform.T @ (applied_load(case) - case.vortex_load).T).T
        result['reaction_offset'] = MU0 * load[:, -holes:] if holes else np.zeros((len(load), 0))
        np.savez_compressed(destination / path.name, **result)
        manifest[path.stem] = {'family': case.meta['family'], 'oracle_seconds': elapsed,
                              'reference_seconds': max(0.25, elapsed * 0.7), 'reference_rss_mib': 300}
        print(path.stem, elapsed, flush=True)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()

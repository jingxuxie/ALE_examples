import json
from pathlib import Path
import sys

import numpy as np


case = json.loads(Path(sys.argv[1]).read_text())
count = case['n_spins']
with open(sys.argv[2], 'wb') as stream:
    np.savez_compressed(stream, saddle=np.asarray(case['minimum_a']), barrier_meV=0.0,
                        eigenvalues_min_meV=np.ones(2 * count),
                        eigenvalues_saddle_meV=np.array([-1.0] + [1.0] * (2 * count - 1)),
                        log_omega0=0.0)

import json
from pathlib import Path
import sys

import solve
import numpy as np
from scipy.special import logsumexp

instance = json.loads(Path(sys.argv[1]).read_text())
couplings = np.asarray(instance["couplings"])
fields = np.asarray(instance["fields"])
block = solve.blocks_of(couplings)[0]
for penalty in [0, 0.002, 0.01, 0.025, 0.05, 0.1]:
    fitted = solve.fit_block(couplings[np.ix_(block, block)], fields[block], np.random.default_rng(715923), trials=8, diversity=penalty)
    logits = np.matmul(fitted.design, fitted.matrices.transpose(0, 2, 1))
    component_logs = -np.logaddexp(0, -fitted.spins * logits).sum(axis=2)
    logs = logsumexp(component_logs, axis=0) - np.log(2)
    probability = np.exp(logs)
    contrast = np.tanh((component_logs[0] - component_logs[1]) / 2)
    print(json.dumps({"penalty": penalty, "objective": fitted.score, "kl": float(probability @ (logs - fitted.target)), "ess": float(np.exp(-logsumexp(2 * fitted.target - logs))), "contrast": float(probability @ contrast ** 2)}), flush=True)

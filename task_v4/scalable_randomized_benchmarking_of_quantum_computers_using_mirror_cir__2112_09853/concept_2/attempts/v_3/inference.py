import glob
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / 'submission'))
from policy import Policy

Policy.sampler_name = '../sampler2.so'
for path in sorted(glob.glob(sys.argv[1])):
    fixture = json.loads(Path(path).read_text())
    policy = Policy(fixture['hello'])
    policy.observations = fixture['observations']
    policy.spent = 2000
    started = time.time()
    posterior = policy.posterior(samples=3072, burn=1800, thin=4)
    unused, features = policy.grid.features(fixture['targets'])
    rates = -np.expm1(-(posterior[:, :policy.rate_dimension] @ features.T))
    truth = np.asarray(fixture['truths'])
    record = dict(fixture=path, seconds=time.time()-started, true_mean=float(truth.mean()), posterior_mean=float(rates.mean()))
    for power in [0, 0.5, 1, 1.5, 2, 2.5, 3]:
        weight = (0.003+0.10*rates)**(-power)
        predictions = np.sum(weight*rates, axis=0)/weight.sum(axis=0)
        record[str(power)] = float(np.mean(((predictions-truth)/(0.003+0.10*truth))**2))
    print(json.dumps(record), flush=True)

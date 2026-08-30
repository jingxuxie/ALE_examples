import json
import sys
from pathlib import Path
import numpy as np
from optimization import FullRefinement
from regional import regions

instance = json.loads(Path(sys.argv[1]).read_text())
model = json.loads(Path(sys.argv[2]).read_text())
couplings = np.asarray(instance['couplings'])
fields = np.asarray(instance['fields'])
blocks = regions(couplings * (abs(couplings) > .65 * np.max(abs(couplings))))
assert len(blocks) == 5 and all(len(block) == 4 for block in blocks)
sites = np.concatenate(blocks)
inverse = np.argsort(sites)
gauge = np.sign(fields[sites])
weights = np.asarray(model['weights'])[:, sites, :][:, :, sites] * gauge[None, :, None] * gauge[None, None, :]
biases = np.asarray(model['biases'])[:, sites] * gauge
orders = inverse[np.asarray(model['orders'])]
initial = {'mixing': model['mixing'], 'weights': weights.tolist(), 'biases': biases.tolist(), 'orders': orders.tolist()}
strength = float(np.median([abs(couplings[first, second]) for block in blocks for first in block for second in block if first < second]))
ideal_couplings = np.zeros((20, 20))
for block in range(5):
    ideal_couplings[4 * block:4 * block + 4, 4 * block:4 * block + 4] = -strength
np.fill_diagonal(ideal_couplings, 0)
ideal = {'n': 20, 'couplings': ideal_couplings.tolist(), 'fields': [strength] * 20}
optimizer = FullRefinement(ideal, initial, seconds=float(sys.argv[4]), verbose=True, threads=4)
fitted = optimizer.fit(iterations=2000)
Path(sys.argv[3]).write_text(json.dumps({'strength': strength, 'model': fitted}, separators=(',', ':')))

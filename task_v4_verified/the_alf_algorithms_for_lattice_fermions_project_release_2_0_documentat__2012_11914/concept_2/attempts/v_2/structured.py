import itertools
import json
import time
import numpy as np
from search import ROOT, write_submission
from optimize import full, tensor
from risk import optimize

data = np.load(ROOT / 'riskgram.npz')
points, projection = data['points'], data['projection']
words = []
for outer in range(5):
    permutations = list(itertools.permutations(component for component in range(5) if component != outer))
    for first in permutations:
        for second in permutations:
            first, second = list(first), list(second)
            word = [outer] + first + first[-2::-1] + [outer] + second + second[-2::-1] + [outer]
            words.append(np.array(word))
np.random.default_rng(811).shuffle(words)
start = time.time()
population = []
best = 1e10
for index, word in enumerate(words):
    result = optimize(word, points, projection, mode='max')
    population.append((float(result.fun), word.tolist(), result.x.tolist()))
    population.sort()
    population = population[:40]
    if result.fun < best:
        best = result.fun
        residual = tensor(word, result.x)[0] @ projection
        losses = (points @ residual) @ residual
        print(index, round(time.time() - start, 2), best, np.sqrt(losses.max()), losses.mean(), ''.join(map(str, word)), flush=True)
        write_submission(*full(word, result.x), name='structuredbest.json')
        (ROOT / 'structuredpopulation.json').write_text(json.dumps(population))
(ROOT / 'structuredpopulation.json').write_text(json.dumps(population))
print('finished', time.time() - start, flush=True)

import json
import numpy as np
from grow_prune import library
from beam import Problem, load_cases, Excitation

problem = Problem(load_cases()[1])
record = json.load(open('sector_10_4_best.json'))
labels = [problem.gates.index(Excitation(tuple(entry['annihilate']), tuple(entry['create']))) for entry in record['gates']]
angles = [entry['theta'] for entry in record['gates']]
value, angles, state = problem.fit(labels, angles, iterations=200)
length = len(labels)
scores = np.zeros((length + 1, len(problem.gates), 2))
library.insertions(problem.dimension, len(problem.gates), problem.stride, problem.sources, problem.destinations, problem.signs, problem.counts, problem.reference, problem.target, length, np.asarray(labels, dtype=np.int32), np.asarray(angles, dtype=float), scores)
saved = 0
for flat_index in np.argsort(scores[:, :, 0], axis=None)[:100]:
    position, label = np.unravel_index(flat_index, scores.shape[:2])
    new_labels = list(labels)
    new_angles = list(angles)
    new_labels.insert(position, int(label))
    new_angles.insert(position, scores[position, label, 1])
    value, fitted, state = problem.fit(new_labels, new_angles, iterations=200)
    if value < 1e-11:
        problem.save(list(reversed(list(zip(new_labels, fitted)))), f'exact19_{saved}.json')
        print('SAVED', saved, position, problem.gates[label], value, flush=True)
        saved += 1
        if saved == 10:
            break

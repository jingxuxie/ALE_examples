import json
import math
import os
import sys
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np

ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
sys.path.insert(0, ASSETS + '/workspace')
from pair_model import increments

orders = np.array([mask.bit_count() for mask in range(256)])
groups = [np.flatnonzero(orders == order) for order in range(9)]
subset = (np.arange(256)[:, None] & np.arange(256)[None, :]) == np.arange(256)[None, :]
models = json.load(open(ASSETS + '/input/practice_models.json'))
data = np.load(ASSETS + '/input/practice.npz')
print('data', [(key, data[key].shape) for key in data.files], flush=True)
energies = data['energies']
terms = np.array([increments(table) for table in energies])
families = np.array([model['family'] for model in models])

def report(name, predictions):
    error = (np.array(predictions) - energies[:, -1]) * 1e6
    print(name, 'all', round(np.sqrt(np.mean(error ** 2)), 3), 'max', round(max(abs(error)), 3), 'families', {family: round(np.sqrt(np.mean(error[families == family] ** 2)), 3) for family in sorted(set(families))}, flush=True)

for order in range(2, 8):
    report('MBE' + str(order), terms[:, orders <= order].sum(axis=1))
baseline = []
for row in terms:
    scores = np.abs(row[groups[3]]) @ subset[groups[4]][:, groups[3]].T
    selected = groups[4][np.argsort(-scores)[:26]]
    baseline.append(row[orders <= 3].sum() + row[selected].sum())
report('baseline', baseline)
for score_order in [1, 2, 3]:
    for power in [0.5, 1, 2]:
        predictions = []
        for row in terms:
            score = np.abs(row) ** power * ((orders >= 1) & (orders <= score_order))
            site_scores = subset[:, groups[1]].T @ score
            excluded = np.argsort(site_scores)[:2]
            mask = 255 ^ (1 << excluded[0]) ^ (1 << excluded[1])
            predictions.append(row[subset[mask] | (orders <= 3)].sum())
        report('6anchor' + str((score_order, power)), predictions)
print('order sums by system')
for index, row in enumerate(terms):
    print(index, families[index], np.round([row[groups[order]].sum() * 1e6 for order in range(3, 9)], 2).tolist())

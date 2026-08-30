import json
import sys
from pathlib import Path
import numpy as np

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
destination.mkdir(exist_ok=True)
settings = [('local_warm', 'local_sectors', .8, .005),
            ('local_cold', 'local_sectors', 1.7, .005),
            ('local_perturbed', 'local_sectors', 1.2, .035),
            ('coupled_cold', 'coupled', 1.15, .07),
            ('coupled_perturbed', 'coupled', .85, .14),
            ('cycles_random', 'cycles', 1.2, .0)]
for case_index, (name, family, scale, noise) in enumerate(settings):
    instance = json.loads((source / ('example_' + family + '.json')).read_text())
    rng = np.random.default_rng(83171 + case_index)
    couplings = np.asarray(instance['couplings']) * scale
    fields = np.asarray(instance['fields']) * scale
    perturbation = rng.normal(0, noise, size=(20, 20))
    perturbation = np.triu(perturbation, 1)
    couplings += perturbation + perturbation.T
    fields += rng.normal(0, 2 * noise, size=20)
    if family == 'cycles':
        signs = np.triu(rng.choice([-1, 1], size=(20, 20)), 1)
        couplings = abs(couplings) * (signs + signs.T)
    gauge = rng.choice([-1, 1], size=20)
    permutation = rng.permutation(20)
    couplings *= gauge[:, None] * gauge[None, :]
    fields *= gauge
    result = {'n': 20, 'couplings': couplings[np.ix_(permutation, permutation)].tolist(),
              'fields': fields[permutation].tolist()}
    (destination / (name + '.json')).write_text(json.dumps(result))

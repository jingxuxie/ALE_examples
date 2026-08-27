import json

import numpy as np

from build_inputs import ROOT, intervention
from cores import detect
from model import Model


hidden = ROOT / 'concept_01/evaluator/hidden'
manifest = json.loads((hidden / 'manifest.json').read_text())
case = manifest['cases'][3]
with np.load(hidden / case['asset']) as data:
    arrays = dict(data)
xx, yy = np.meshgrid(arrays['x'], arrays['y'])
radius = np.hypot(xx, yy)
arrays['roi'] = ((radius > 6.3) & (radius < 11.0)).astype(int)
arrays['bulk'] = (radius > 7.3) & (radius < 9.8)
np.savez_compressed(hidden / case['asset'], **arrays)
model = Model(case, arrays)
cores = detect(arrays['psi'], model)
case = intervention(case, cores, 'annular_current', target=(8, 0), charge=-2)
manifest['cases'][3] = case
(hidden / 'manifest.json').write_text(json.dumps(manifest, indent=2))
(hidden / 'annulus_only.json').write_text(json.dumps(dict(cases=[case]), indent=2))
print('annular supported cores:', len(cores), 'bulk:', np.count_nonzero(model.sample(model.bulk, cores[:, :2])))

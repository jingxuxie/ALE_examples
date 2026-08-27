import json

from build_inputs import ROOT, create_state, intervention


hidden = ROOT / 'concept_01/evaluator/hidden'
manifest = json.loads((hidden / 'manifest.json').read_text())
annulus, cores = create_state(hidden, 'annulus_state', 'annulus', 160, 160, 28, 28, 700, 0.85, 3000)
annulus = intervention(annulus, cores, 'annular_current', target=(6, 0), charge=-2)
annulus['times'] = [0, 0.1, 0.6, 1.8, 4]
doublewell, cores = create_state(hidden, 'doublewell_state', 'doublewell', 192, 160, 28, 24, 700, 0.85, 3000)
doublewell = intervention(doublewell, cores, 'split_domains', target=(6.3, 0))
doublewell['times'] = [0, 0.1, 0.5, 1.4, 3]
manifest['cases'] = manifest['cases'][:3] + [annulus, doublewell]
(hidden / 'manifest.json').write_text(json.dumps(manifest, indent=2))

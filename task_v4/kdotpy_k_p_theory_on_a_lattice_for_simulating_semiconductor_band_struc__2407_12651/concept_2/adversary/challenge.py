import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from model import diagnose


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--witness', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--samples', type=int, default=1200)
    parser.add_argument('--radius', type=float, default=.02)
    parser.add_argument('--seed', type=int, default=928781)
    parser.add_argument('--corners', action='store_true')
    options = parser.parse_args()
    parameters = np.array(json.loads(Path(options.witness).read_text())['parameters'])
    generator = np.random.default_rng(options.seed)
    started = time.monotonic()
    families = {'mass_offset': list(range(9)), 'dispersion': list(range(9, 13)),
                'hybridization': list(range(13, 21)), 'mixed': list(range(21))}
    records = []
    worst = {}
    for trial in range(options.samples):
        family = list(families)[trial % len(families)]
        displacement = np.zeros(25)
        coordinates = families[family]
        displacement[coordinates] = (generator.choice([-options.radius, options.radius], len(coordinates))
                                     if options.corners else generator.uniform(-options.radius, options.radius, len(coordinates)))
        metrics = diagnose(parameters + displacement, 41)
        record = {'family': family, 'trial': trial, 'displacement': displacement.tolist(),
                  'metrics': metrics}
        records.append(record)
        if family not in worst or metrics['plateau_spread'] > worst[family]['metrics']['plateau_spread']:
            worst[family] = record
    refined = {}
    for family, record in worst.items():
        record['fine_metrics'] = diagnose(parameters + np.array(record['displacement']), 129, (.39, .13))
        refined[family] = record
    result = {'radius': options.radius, 'samples': options.samples, 'seed': options.seed,
              'distribution': 'box corners' if options.corners else 'uniform box',
              'elapsed_seconds': time.monotonic() - started,
              'scientific_scope': 'Finite-range Hermitian model under simultaneous bounded coefficient changes, not generation-1 required points',
              'failure_counts': {family: sum(record['metrics']['plateau_spread'] > .009 for record in records if record['family'] == family)
                                 for family in families}, 'worst_by_family': refined,
              'root_causes': ['spectral-window cancellation sensitivity', 'simultaneous perturbations absent from axis-only audit']}
    Path(options.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

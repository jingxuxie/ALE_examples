import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import json
import resource
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from check import check


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024 ** 3, 8 * 1024 ** 3))


def make_stress(source, destination, seed, scale, cross_scale, disorder):
    instance = json.loads(source.read_text())
    rng = np.random.default_rng(seed)
    count = instance['n']
    couplings = np.asarray(instance['couplings'])
    fields = np.asarray(instance['fields'])
    strong = np.abs(couplings) > 0.25
    noise = rng.normal(size=(count, count))
    noise = (noise + noise.T) / np.sqrt(2)
    couplings = scale * couplings * np.where(strong, 1, cross_scale)
    couplings += disorder * noise * strong
    np.fill_diagonal(couplings, 0)
    fields = scale * fields + disorder * rng.normal(size=count)
    permutation = rng.permutation(count)
    gauge = rng.choice([-1, 1], size=count)
    couplings = couplings[np.ix_(permutation, permutation)] * gauge[:, None] * gauge[None, :]
    fields = fields[permutation] * gauge
    instance['couplings'] = couplings.tolist()
    instance['fields'] = fields.tolist()
    destination.write_text(json.dumps(instance, separators=(',', ':')))


def main():
    public = Path(sys.argv[1])
    refit = '--refit' in sys.argv[2:]
    print('Environment', resource.getrlimit(resource.RLIMIT_AS), sorted(os.sched_getaffinity(0)), flush=True)
    destination = Path('validation')
    destination.mkdir(exist_ok=True)
    cases = []
    for family_index, family in enumerate(('quartets', 'quintets', 'mixed')):
        original = public / ('example_' + family + '.json')
        cases.append((family, 'public', original))
        for variant, scale, cross_scale, disorder in (('warm', 0.8, 2, 0.05), ('cold_disordered', 1.2, 4, 0.10)):
            stress_path = destination / (family + '_' + variant + '_instance.json')
            make_stress(original, stress_path, 85291 + 47 * family_index + int(scale * 100), scale, cross_scale, disorder)
            cases.append((family, variant, stress_path))
    results = []
    for family, variant, instance_path in cases:
        model_path = destination / (family + '_' + variant + '_model.json')
        log_path = destination / (family + '_' + variant + '.log')
        if refit or not model_path.exists():
            started = time.monotonic()
            environment = os.environ.copy()
            environment['SOLVE_VERBOSE'] = '1'
            with log_path.open('w') as output:
                subprocess.run([sys.executable, 'solve.py', str(instance_path), str(model_path)],
                               stdout=output, stderr=subprocess.STDOUT, timeout=120, check=True,
                               preexec_fn=limits, env=environment)
            seconds = time.monotonic() - started
        else:
            seconds = None
        metrics = check(instance_path, model_path)
        metrics.update({'family': family, 'variant': variant, 'solve_seconds': seconds})
        results.append(metrics)
        (destination / 'results.json').write_text(json.dumps(results, indent=2))
        print('RESULT', json.dumps(metrics), flush=True)


if __name__ == '__main__':
    main()

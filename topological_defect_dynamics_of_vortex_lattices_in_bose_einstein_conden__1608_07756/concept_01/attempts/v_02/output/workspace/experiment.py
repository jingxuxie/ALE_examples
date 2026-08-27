import csv
import json
import resource
import time
from pathlib import Path

import numpy as np

from cores import detect
from current import measure
from model import Model, imprint
from order import characterize
from propagate import Propagator


FIELDS = ['case', 'frame', 'time', 'norm', 'r2', 'energy', 'Ec', 'Ei', 'Eq', 'nplus', 'nminus', 'n5', 'n6', 'n7', 'g6_near', 'g6_far', 'defect_radius']


def write_csv(path, rows, fields=None):
    with open(path, 'w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(manifest_path, output_path, configuration):
    manifest_path = Path(manifest_path).resolve()
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text())
    rows, scaling = [], []
    for case in manifest['cases']:
        started = time.perf_counter()
        cpu_started = time.process_time()
        with np.load(manifest_path.parent / case['asset']) as arrays:
            model = Model(case, arrays)
            initial = imprint(arrays['psi'].copy(), model, case.get('imprints', []))
        propagator = Propagator(model, configuration)
        frames = propagator.evolve(initial, case['times'], configuration.get('dt', 0.002))
        diagnostics = []
        for frame_index, (time_value, frame) in enumerate(zip(case['times'], frames)):
            cores = detect(frame, model)
            topology = characterize(cores, model)
            physics = measure(frame, model, time_value)
            selected = model.sample(model.bulk, cores[:, :2])
            row = {'case': case['id'], 'frame': frame_index, 'time': time_value}
            row.update({key: physics[key] for key in ['norm', 'r2', 'energy', 'Ec', 'Ei', 'Eq']})
            row.update(nplus=int(np.sum(selected & (cores[:, 2] > 0))), nminus=int(np.sum(selected & (cores[:, 2] < 0))))
            row.update({f'n{coordination}': topology['counts'][coordination] for coordination in [5, 6, 7]})
            row.update(g6_near=topology['correlations'][0], g6_far=topology['correlations'][-1], defect_radius=topology['defect_radius'])
            rows.append(row)
            diagnostics.append(dict(cores=cores.tolist(), topology=topology, physics=physics))
        np.savez_compressed(output / (case['id'] + '.npz'), psi=frames, times=case['times'])
        (output / (case['id'] + '.json')).write_text(json.dumps(diagnostics, indent=2, allow_nan=False))
        scaling.append({'case': case['id'], 'nx': len(model.x), 'ny': len(model.y), 'dt': propagator.max_step, 'frames': len(frames), 'wall_seconds': time.perf_counter() - started, 'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
        scaling[-1].update(cpu_seconds=time.process_time() - cpu_started, steps=propagator.steps)
        print(f"{case['id']}: {scaling[-1]['wall_seconds']:.3f}s, {propagator.steps} steps", flush=True)
    write_csv(output / 'results.csv', rows, FIELDS)
    write_csv(output / 'scaling.csv', scaling)
    (output / 'configuration.json').write_text(json.dumps(configuration, indent=2))
    return rows, scaling

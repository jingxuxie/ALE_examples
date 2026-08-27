import csv
import hashlib
import importlib.util
import importlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import scipy
import PIL
from scipy.optimize import linear_sum_assignment

from audit import audit
from experiment import FIELDS, write_csv
from model import Model


ROOT = Path(__file__).resolve().parent.parent


def read_rows(path):
    return list(csv.DictReader(Path(path).open()))


def comparison(manifest, first_run, second_run):
    records = []
    for case in json.loads(manifest.read_text())['cases']:
        with np.load(manifest.parent / case['asset']) as asset:
            area = float((asset['x'][1] - asset['x'][0]) * (asset['y'][1] - asset['y'][0]))
        first_frames = np.load(first_run / (case['id'] + '.npz'))['psi']
        second_frames = np.load(second_run / (case['id'] + '.npz'))['psi']
        first_json = json.loads((first_run / (case['id'] + '.json')).read_text())
        second_json = json.loads((second_run / (case['id'] + '.json')).read_text())
        for frame, (first, second) in enumerate(zip(first_frames, second_frames)):
            phase = np.angle(np.vdot(second, first))
            aligned = first * np.exp(-1j * phase)
            first_cores = np.asarray(first_json[frame]['cores']).reshape((-1, 3))
            second_cores = np.asarray(second_json[frame]['cores']).reshape((-1, 3))
            distances = []
            count_difference = 0
            for charge in (-1, 1):
                first_positions = first_cores[first_cores[:, 2] == charge, :2]
                second_positions = second_cores[second_cores[:, 2] == charge, :2]
                count_difference += abs(len(first_positions) - len(second_positions))
                if len(first_positions) and len(second_positions):
                    cost = np.linalg.norm(first_positions[:, None, :] - second_positions[None, :, :], axis=2)
                    first_indices, second_indices = linear_sum_assignment(cost)
                    distances.extend(cost[first_indices, second_indices].tolist())
            records.append(dict(case=case['id'], frame=frame, time=case['times'][frame],
                                wave_l2=float(np.sqrt(area * np.sum(abs(aligned - second) ** 2))),
                                density_relative_l2=float(np.linalg.norm(abs(first) ** 2 - abs(second) ** 2) / np.linalg.norm(abs(second) ** 2)),
                                max_density_difference=float(np.max(abs(abs(first) ** 2 - abs(second) ** 2))),
                                signed_core_count_difference=count_difference,
                                matched_core_rms=float(np.sqrt(np.mean(np.array(distances) ** 2))) if distances else 0.0,
                                g6_max_difference=float(np.max(abs(np.array(first_json[frame]['topology']['correlations'])
                                                                  - np.array(second_json[frame]['topology']['correlations']))))))
    return records


def healing(manifest, run):
    case = json.loads(manifest.read_text())['cases'][0]
    with np.load(manifest.parent / case['asset']) as asset:
        grid_x, grid_y = np.meshgrid(asset['x'], asset['y'])
        area = float((asset['x'][1] - asset['x'][0]) * (asset['y'][1] - asset['y'][0]))
    radius = np.hypot(grid_x, grid_y)
    central = radius < 0.35
    annulus = (radius >= 0.7) & (radius < 1.0)
    frames = np.load(run / (case['id'] + '.npz'))['psi']
    records = []
    for frame, psi in enumerate(frames):
        density = abs(psi) ** 2
        central_density = density[central].mean()
        annular_density = density[annulus].mean()
        records.append(dict(case=case['id'], frame=frame, time=case['times'][frame],
                            core_mean_density=float(central_density), annular_mean_density=float(annular_density),
                            core_to_annulus_ratio=float(central_density / annular_density),
                            core_mass=float(area * density[central].sum()), peak_density=float(density.max())))
    return records


def old_measurements(manifest, run, legacy=True):
    modules = {}
    for name in ('cores', 'current', 'order'):
        if not legacy:
            modules[name] = importlib.import_module(name)
            continue
        location = ROOT / 'experiments/baseline/workspace' / (name + '.py')
        specification = importlib.util.spec_from_file_location('baseline_' + name, location)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        modules[name] = module
    records = []
    for case in json.loads(manifest.read_text())['cases']:
        with np.load(manifest.parent / case['asset']) as asset:
            model = Model(case, asset)
        frames = np.load(run / (case['id'] + '.npz'))['psi']
        for frame, psi in enumerate(frames):
            cores = modules['cores'].detect(psi, model)
            topology = modules['order'].characterize(cores, model)
            physics = modules['current'].measure(psi, model, case['times'][frame])
            selected = model.sample(model.bulk, cores[:, :2])
            row = dict(case=case['id'], frame=frame, time=case['times'][frame])
            row.update({name: physics[name] for name in ('norm', 'r2', 'energy', 'Ec', 'Ei', 'Eq')})
            row.update(nplus=int(np.sum(selected & (cores[:, 2] > 0))), nminus=int(np.sum(selected & (cores[:, 2] < 0))))
            row.update({f'n{degree}': topology['counts'][degree] for degree in (5, 6, 7)})
            row.update(g6_near=topology['correlations'][0], g6_far=topology['correlations'][-1], defect_radius=topology['defect_radius'])
            records.append(row)
    return records


def main():
    experiments = ROOT / 'experiments'
    campaign = ROOT / 'inputs/campaign.json'
    calibration = ROOT / 'inputs/calibration.json'
    transfer = experiments / 'transfer_input/manifest.json'
    shutil.copyfile(experiments / 'primary/results.csv', ROOT / 'results.csv')
    shutil.copyfile(experiments / 'ablation/results.csv', ROOT / 'ablation.csv')
    shutil.copyfile(experiments / 'refinement/results.csv', ROOT / 'refinement.csv')
    scaling = []
    for variant in ('primary', 'ablation', 'refinement'):
        for row in read_rows(experiments / variant / 'scaling.csv'):
            scaling.append(dict(variant=variant, **row))
    write_csv(ROOT / 'scaling.csv', scaling)
    convergence = []
    audit_rows = []
    for manifest, prefix in ((campaign, ''), (calibration, 'calibration_'), (transfer, 'transfer_')):
        convergence.extend(comparison(manifest, experiments / (prefix + 'primary'), experiments / (prefix + 'refinement')))
        for variant in ('primary', 'refinement'):
            rows = audit(manifest, experiments / (prefix + variant), experiments / (prefix + variant) / 'audit.csv')
            if variant == 'primary':
                audit_rows.extend(rows)
    audit(campaign, experiments / 'ablation', experiments / 'ablation/audit.csv')
    write_csv(ROOT / 'convergence.csv', convergence)
    write_csv(ROOT / 'audit.csv', audit_rows)
    write_csv(ROOT / 'ablation_sensitivity.csv', comparison(campaign, experiments / 'ablation', experiments / 'refinement'))
    coarse = comparison(campaign, experiments / 'coarse', experiments / 'refinement')
    coarse.extend(comparison(calibration, experiments / 'calibration_coarse', experiments / 'calibration_refinement'))
    coarse.extend(comparison(transfer, experiments / 'transfer_coarse', experiments / 'transfer_refinement'))
    write_csv(ROOT / 'coarse_sensitivity.csv', coarse)
    write_csv(ROOT / 'healing.csv', healing(calibration, experiments / 'calibration_primary'))
    write_csv(ROOT / 'baseline_healing.csv', healing(calibration, experiments / 'baseline/calibration'))
    old_rows = old_measurements(campaign, experiments / 'primary')
    old_rows.extend(old_measurements(calibration, experiments / 'calibration_primary'))
    write_csv(ROOT / 'measurement_only.csv', old_rows, FIELDS)
    write_csv(ROOT / 'baseline_remeasured.csv', old_measurements(calibration, experiments / 'baseline/calibration', legacy=False), FIELDS)
    ultrafine_manifest = experiments / 'ultrafine_input/manifest.json'
    higher_primary = comparison(ultrafine_manifest, experiments / 'primary', experiments / 'ultrafine')
    higher_refinement = comparison(ultrafine_manifest, experiments / 'refinement', experiments / 'ultrafine')
    higher = []
    for first, second in zip(higher_primary, higher_refinement):
        higher.append(dict(case=first['case'], frame=first['frame'], time=first['time'],
                           primary_vs_ultrafine_wave_l2=first['wave_l2'],
                           refinement_vs_ultrafine_wave_l2=second['wave_l2'],
                           primary_vs_ultrafine_density_l2=first['density_relative_l2'],
                           refinement_vs_ultrafine_density_l2=second['density_relative_l2']))
    write_csv(ROOT / 'higher_refinement.csv', higher)
    source_hashes = {}
    for directory in (ROOT / 'inputs', ROOT / 'workspace'):
        for path in sorted(directory.glob('*')):
            if path.is_file():
                source_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ['run.sh', 'reproduce.sh', 'config.json', 'ablation_config.json', 'refinement_config.json']:
        source_hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    versions = dict(python=sys.version, numpy=np.__version__, scipy=scipy.__version__, pillow=PIL.__version__)
    (ROOT / 'provenance.json').write_text(json.dumps(dict(versions=versions, sha256=source_hashes), indent=2))
    print('Handoff tables regenerated.')


if __name__ == '__main__':
    main()

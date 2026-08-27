import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.special import expit


ROOT = Path(__file__).resolve().parents[1]
TRUE_MODEL = {
    'offsets': np.log(np.asarray([[0.025, 0.17, 0.05], [0.16, 0.025, 0.09], [0.04, 0.05, 0.23]])
                      / (1 - np.asarray([[0.025, 0.17, 0.05], [0.16, 0.025, 0.09], [0.04, 0.05, 0.23]]))).tolist(),
    'slopes': [0.9, -0.6, 0.4], 'initial': [0.45, 0.35, 0.2],
    'transition': [[0.90, 0.06, 0.04], [0.05, 0.91, 0.04], [0.07, 0.08, 0.85]],
}


def save(path, content):
    path.write_text(json.dumps(content, indent=2, allow_nan=False) + '\n')


def apply_new(path, content):
    patch = '*** Begin Patch\n*** Add File: ' + str(path) + '\n'
    patch += ''.join('+' + line + '\n' for line in content.splitlines()) + '*** End Patch\n'
    subprocess.run(['apply_patch'], input=patch, text=True, check=True, capture_output=True)


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def resample(case, seed, doses):
    random = np.random.default_rng(seed)
    case.pop('mode_prior')
    for fault in case['faults']:
        fault.pop('probabilities')
        fault['rate_group'] = int(random.integers(3))
        fault['bias'] = float(random.choice([-0.25, 0.0, 0.25]))
    offsets = np.asarray(TRUE_MODEL['offsets'])
    slopes = np.asarray(TRUE_MODEL['slopes'])
    mode = int(random.choice(3, p=TRUE_MODEL['initial']))
    groups = np.asarray([fault['rate_group'] for fault in case['faults']])
    biases = np.asarray([fault['bias'] for fault in case['faults']])
    for index, shot in enumerate(case['shots']):
        if index:
            mode = int(random.choice(3, p=TRUE_MODEL['transition'][mode]))
        dose = doses[index % len(doses)]
        shot['dose'] = dose
        rates = expit(offsets[mode, groups] + slopes[groups] * dose + biases)
        syndrome = [0] * case['num_detectors']
        for fault, rate in zip(case['faults'], rates):
            if random.random() < rate:
                for detector in fault['detectors']:
                    syndrome[detector] ^= 1
        for detector, old in enumerate(shot['syndrome']):
            if old is None:
                syndrome[detector] = None
        shot['syndrome'] = syndrome
    return case


def calibration():
    random = np.random.default_rng(380127)
    probes = []
    for probe_index, detector_count in enumerate([6, 7, 8]):
        faults = []
        for index in range(12):
            support = random.choice(detector_count, int(random.integers(2, 5)), replace=False).tolist()
            faults.append({'detectors': sorted(support), 'rate_group': index % 3,
                           'bias': float(random.choice([-0.25, 0.0, 0.25]))})
        probes.append({'id': f'probe_{probe_index}', 'num_detectors': detector_count, 'faults': faults})
    settings = [{'probe': probe['id'], 'dose': dose} for probe in probes for dose in [-0.8, 0.0, 0.8]]
    metadata = {'rate_groups': 3, 'max_modes': 3, 'probes': probes, 'settings': settings,
                'records': {'arrays': ['setting', 'syndrome'], 'shape': [12000, 5],
                            'encoding': 'syndrome integers use detector zero as the least significant bit'}}
    selected_settings = random.integers(len(settings), size=(12000, 5), dtype=np.int16)
    syndromes = np.zeros_like(selected_settings)
    offsets = np.asarray(TRUE_MODEL['offsets'])
    slopes = np.asarray(TRUE_MODEL['slopes'])
    modes = random.choice(3, size=12000, p=TRUE_MODEL['initial'])
    for step in range(5):
        if step:
            uniforms = random.random(len(modes))
            transition = np.asarray(TRUE_MODEL['transition'])
            modes = (uniforms[:, None] > transition[modes].cumsum(axis=1)).sum(axis=1)
        for setting_index, setting in enumerate(settings):
            selected = np.flatnonzero(selected_settings[:, step] == setting_index)
            probe = probes[setting_index // 3]
            for fault in probe['faults']:
                group = fault['rate_group']
                rates = expit(offsets[modes[selected], group] + slopes[group] * setting['dose'] + fault['bias'])
                bits = random.random(len(selected)) < rates
                syndromes[selected, step] ^= bits.astype(np.int16) * sum(1 << detector for detector in fault['detectors'])
    return metadata, selected_settings, syndromes


def main():
    generator = load_module('generator_v1', ROOT / 'authoring/build_inputs.py')
    public = ROOT / 'participant/v_02/input'
    metadata, settings, syndromes = calibration()
    save(public / 'calibration.json', metadata)
    np.savez_compressed(public / 'calibration_records.npz', setting=settings, syndrome=syndromes)
    save(ROOT / 'authoring/true_model_v02.json', TRUE_MODEL)
    micro = [resample(generator.generate_case(188 + index, f'micro_{index}', 3, 2, 1,
                                                [(0, 1), (1, 2), (2, 0)], shot_count=3, tiny=True),
                       1409 + index, [-0.8, 0.8, 0.0]) for index in range(3)]
    validation = [
        resample(generator.generate_case(1308, 'dose_ring', 4, 12, 6,
                                          [(0, 1), (1, 2), (2, 3), (3, 0)], shot_count=4),
                 621, [-0.8, 0.0, 0.8, -0.8]),
        resample(generator.generate_case(1612, 'drift_ladder', 6, 16, 7,
                                          [(0, 1), (1, 2), (3, 4), (4, 5), (0, 3), (1, 4), (2, 5)], shot_count=5),
                 827, [0.8, 0.0, -0.8, 0.8, 0.0]),
    ]
    hidden = [
        resample(generator.generate_case(734512, 'h_long_ring', 7, 16, 7,
                                          [(index, (index + 1) % 7) for index in range(7)] + [(1, 4)], shot_count=6),
                 87781, [-1.3, 0.4, 1.3, 0.0, -1.1, 1.1]),
        resample(generator.generate_case(612909, 'h_new_junction', 9, 17, 7,
                                          [(row * 3 + column, row * 3 + column + 1) for row in range(3) for column in range(2)]
                                          + [(row * 3 + column, (row + 1) * 3 + column) for row in range(2) for column in range(3)],
                                          shot_count=5), 991728, [1.4, -0.3, 0.5, -1.4, 0.9]),
        resample(generator.generate_case(791829, 'h_temporal_shift', 3, 2, 2,
                                          [(0, 1), (1, 2), (2, 0)], shot_count=7, tiny=True),
                 101882, [0.0, 1.2, -1.2, 0.7, -0.7, 1.4, -1.4]),
    ]
    for shot_index in (1, 4):
        hidden[-1]['shots'][shot_index]['syndrome'] = [None] * hidden[-1]['num_detectors']
    save(public / 'micro.json', {'cases': micro})
    save(public / 'validation.json', {'cases': validation})
    for index, case in enumerate(hidden, 1):
        save(ROOT / f'evaluator/v_02/hidden/case_{index:02d}.json', {'cases': [case]})
    kernel = (ROOT / 'solution/v_01/solve.py').read_text()
    kernel = kernel[:kernel.index('\ndef solve_case(case):')]
    apply_new(ROOT / 'solution/v_02/local_kernel.py', kernel)
    sys.path.insert(0, str(ROOT / 'solution/v_02'))
    decoder = load_module('decoder_v02', ROOT / 'solution/v_02/solve.py')
    micro_truth = decoder.solve_dataset({'cases': micro}, TRUE_MODEL)
    public_truth = decoder.solve_dataset({'cases': validation}, TRUE_MODEL)
    save(public / 'micro_expected.json', micro_truth)
    save(public / 'validation_expected.json', public_truth)
    save(ROOT / 'evaluator/v_02/hidden/public_expected.json', public_truth)
    for index, case in enumerate(hidden, 1):
        save(ROOT / f'evaluator/v_02/hidden/case_{index:02d}_expected.json', decoder.solve_dataset({'cases': [case]}, TRUE_MODEL))
    print(json.dumps({'calibration_sequences': len(settings), 'hidden_faults': [len(case['faults']) for case in hidden]}))


if __name__ == '__main__':
    main()

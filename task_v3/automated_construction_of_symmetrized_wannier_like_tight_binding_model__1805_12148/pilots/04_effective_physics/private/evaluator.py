import argparse
import importlib.util
import json
import pathlib
import sys
import tempfile
import zipfile

import numpy as np


PRIVATE = pathlib.Path(__file__).resolve().parent
PILOT = PRIVATE.parent
ROOT = PILOT.parents[1]
sys.path.insert(0, str(PRIVATE / 'reference'))
from upstream import gauge_residual, rotate_basis


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


LEGACY = load_module('legacy', PILOT / 'participant/workspace/legacy_export.py')
SANDBOX = load_module('sandbox_exec', ROOT / 'authoring/sandbox_exec.py')


def norm(value):
    return float(np.linalg.norm(value))


def read_prediction(path):
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > 32 or sum(member.file_size for member in archive.infolist()) > 64 * 1024 ** 2:
            raise ValueError('Oversized prediction archive')
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in ['U', 'H0', 'H1', 'H2', 'H3', 'G'] if key in archive}


def relative_skill(error, weak_error, reference_error=0.0, floor=1e-9):
    scale = max(weak_error, floor)
    return float((scale + 9 * reference_error) / (scale + 9 * error))


def score(case, reference, prediction):
    dimension = len(case['target'])
    required_shapes = {'U': (dimension, dimension), 'H0': (dimension, dimension), 'H1': (dimension, dimension, 3), 'H2': (dimension, dimension, 3, 3), 'H3': (dimension, dimension, 3, 3, 3), 'G': (dimension, dimension, 3)}
    for key, shape in required_shapes.items():
        if key not in prediction or prediction[key].shape != shape or not np.isfinite(prediction[key]).all() or np.max(np.abs(prediction[key])) > 1e100:
            return {'core_score': 0.0, 'error': 'missing, nonfinite or wrong-shape array: ' + key}
    raw_unitary = prediction['U']
    if np.max(np.abs(raw_unitary)) > 100:
        return {'core_score': 0.0, 'error': 'Nonunitary basis matrix'}
    left, singular, right = np.linalg.svd(raw_unitary)
    unitary = left @ right
    unitarity_error = norm(raw_unitary.conj().T @ raw_unitary - np.eye(dimension)) / np.sqrt(dimension)
    weak = LEGACY.export(case)
    components = {}
    errors = {}
    weak_errors = {}
    reference_gauge_error = gauge_residual(case, reference['U'])
    gauge_error = gauge_residual(case, unitary)
    weak_gauge_error = gauge_residual(case, np.eye(dimension, dtype=complex))
    components['basis'] = relative_skill(gauge_error, weak_gauge_error, reference_gauge_error, floor=0.05)
    errors['basis'] = gauge_error
    weak_errors['basis'] = weak_gauge_error
    for key in ['H2', 'H3', 'G']:
        expected = rotate_basis(reference[key], unitary)
        error = norm(prediction[key] - expected)
        weak_error = norm(weak[key] - reference[key])
        components[key] = relative_skill(error, weak_error, floor=1e-7)
        errors[key] = error
        weak_errors[key] = weak_error
    consistency_error = max(norm(prediction[key] - rotate_basis(reference[key], unitary)) / max(1, norm(reference[key])) for key in ['H0', 'H1'])
    hermiticity_error = max(norm(prediction[key] - prediction[key].swapaxes(0, 1).conj()) / max(1, norm(reference[key])) for key in ['H0', 'H1', 'H2', 'H3', 'G'])
    consistency = 1 / (1 + 1e4 * consistency_error)
    physical = 1 / (1 + 1e4 * unitarity_error + 1e3 * hermiticity_error)
    core = float(np.mean(list(components.values()))) * consistency * physical
    return {'core_score': core, 'component_scores': components, 'errors': errors, 'weak_errors': weak_errors, 'reference_gauge_error': reference_gauge_error, 'unitarity_error': unitarity_error, 'consistency_error': consistency_error, 'hermiticity_error': hermiticity_error}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission')
    parser.add_argument('--split', choices=['test', 'challenge', 'confirmation', 'all'], default='test')
    parser.add_argument('--output', required=True)
    parser.add_argument('--reference', action='store_true')
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--families', nargs='*')
    arguments = parser.parse_args()
    manifest = json.loads((PRIVATE / 'challenge_pool/manifest.json').read_text())
    rows = []
    for record in manifest:
        if arguments.split != 'all' and record['split'] != arguments.split:
            continue
        if arguments.families and record['family'] not in arguments.families:
            continue
        case = dict(np.load(PRIVATE / record['input'], allow_pickle=False))
        reference = dict(np.load(PRIVATE / record['reference'], allow_pickle=False))
        execution = {}
        if arguments.reference:
            prediction = {key: rotate_basis(value, reference['U']) for key, value in reference.items() if key != 'U'}
            prediction['U'] = reference['U']
        elif arguments.baseline:
            prediction = LEGACY.export(case)
        else:
            if not arguments.submission:
                parser.error('--submission is required unless evaluating a reference/baseline')
            directory = pathlib.Path(tempfile.mkdtemp(prefix=record['id'] + '_', dir=PRIVATE / 'reference/runs'))
            output_path = directory / 'result.npz'
            execution = SANDBOX.run_submission(pathlib.Path(arguments.submission) / 'solve.py', PRIVATE / record['input'], output_path, PILOT / 'participant')
            prediction = {}
            if execution['returncode'] == 0 and output_path.exists():
                try:
                    prediction = read_prediction(output_path)
                except Exception as error:
                    execution['read_error'] = str(error)
        result = score(case, reference, prediction)
        rows.append({**record, **result, **execution})
        print(record['id'], result['core_score'], flush=True)
    families = {}
    for family in sorted({row['family'] for row in rows}):
        families[family] = float(np.mean([row['core_score'] for row in rows if row['family'] == family]))
    report = {'core_score': float(np.mean([row['core_score'] for row in rows])) if rows else 0.0, 'worst_family_score': min(families.values()) if families else 0.0, 'family_scores': families, 'cases': rows, 'split': arguments.split, 'reference': arguments.reference, 'baseline': arguments.baseline, 'submission': arguments.submission, 'case_count': len(rows)}
    pathlib.Path(arguments.output).write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'cases'}, indent=2))


if __name__ == '__main__':
    (PRIVATE / 'reference/runs').mkdir(parents=True, exist_ok=True)
    main()

import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import ast
import hashlib
import inspect
import itertools
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import textwrap
import warnings

sys.dont_write_bytecode = True
PILOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PILOT / 'participant/workspace'))
sys.path.insert(0, str(PILOT / 'private'))

import numpy as np

from author_tools import store_json
from compat import load_source
from evaluator import score_result
from geometry import assemble
from hamiltonian import solve_request


def independent_edge(tag, geometry):
    period = geometry['z_x']
    amplitude = geometry['z_y']
    spacing = geometry['a']
    width = geometry['W']
    offset = (width / math.cos(math.atan(4 * amplitude / period)) if amplitude else width) // 2

    def middle(position):
        horizontal, vertical = position
        shifted = horizontal + period / 4
        if shifted % period < period / 2:
            height = 4 * amplitude / period * (shifted % (period / 2)) - amplitude
        else:
            height = -4 * amplitude / period * (shifted % (period / 2)) + amplitude
        return 0 <= horizontal < geometry['L_x'] and height - offset <= vertical < height + offset

    def top(position):
        horizontal, vertical = position
        return not middle(position) and 0 <= horizontal < geometry['L_x'] and vertical < geometry['L_sc_up'] + offset + amplitude

    def bottom(position):
        horizontal, vertical = position
        return not middle(position) and 0 <= horizontal < geometry['L_x'] and vertical >= -geometry['L_sc_down'] - offset - amplitude

    position = (tag[0] * spacing, tag[1] * spacing)
    neighbors = [(position[0] + delta_x * spacing, position[1] + delta_y * spacing)
                 for delta_x, delta_y in itertools.product((-1, 0, 1), repeat=2)
                 if (delta_x, delta_y) != (0, 0)]
    return float(middle(position) and not all(middle(neighbor) for neighbor in neighbors)
                 and not top(position) and any(top(neighbor) for neighbor in neighbors)
                 and not bottom(position) and any(bottom(neighbor) for neighbor in neighbors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-repo', type=Path, required=True)
    parser.add_argument('--write', action='store_true')
    arguments = parser.parse_args()
    provenance = json.loads((PILOT / 'private/reference/SOURCE_MANIFEST.json').read_text())
    for record in provenance['files']:
        content = (PILOT / record['path']).read_bytes()
        assert hashlib.sha256(content).hexdigest() == record['sha256']
        original = subprocess.check_output(['git', '-C', str(arguments.source_repo), 'show', record['revision'] + ':' + record['source_path']])
        assert content == original
    license_bytes = subprocess.check_output(['git', '-C', str(arguments.source_repo), 'show', provenance['license_revision'] + ':LICENSE.txt'])
    assert hashlib.sha256(license_bytes).hexdigest() == provenance['license_sha256']
    for location in ('participant/workspace', 'private/reference'):
        assert (PILOT / location / 'upstream/LICENSE.txt').read_bytes().rstrip(b'\n') == license_bytes.rstrip(b'\n')
    commits = {}
    for revision in ('7bc79e9', '06acb1b', '00b1c82', 'ff2b0e0'):
        full = subprocess.check_output(['git', '-C', str(arguments.source_repo), 'rev-parse', revision], text=True).strip()
        subprocess.run(['git', '-C', str(arguments.source_repo), 'merge-base', '--is-ancestor', full, provenance['reference']], check=True)
        commits[revision] = full
    syntax_files = 0
    for path in PILOT.rglob('*.py'):
        if '.revision-runtime-' not in str(path):
            ast.parse(path.read_text(), filename=str(path))
            syntax_files += 1
    source = load_source(PILOT / 'private/reference/upstream/zigzag.py', PILOT / 'private/reference')
    pool = PILOT / 'private/challenge_pool'
    manifest = json.loads((pool / 'manifest.json').read_text())
    records = []
    for case in manifest['cases']:
        request = json.loads((pool / case['request']).read_text())
        expected = json.loads((pool / case['expected']).read_text())
        weak = json.loads((pool / case['weak']).read_text())
        assert score_result(expected, expected, request, case['weak_rmse'])[0] == 1
        assert abs(score_result(weak, expected, request, case['weak_rmse'])[0] - 0.01) < 1e-12
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            system = assemble(source, request['geometry'])
            result = solve_request(source, request)
        assert score_result(result, expected, request, case['weak_rmse'])[0] > 0.999999
        params = dict(source.constants, **request['model'])
        record = dict(name=case['name'], sites=len(system.sites))
        if request['kind'] == 'barrier':
            direct = [independent_edge(tag, request['geometry']) for tag in request['probes']]
            record['independent_edge_max_error'] = float(np.max(np.abs(np.asarray(direct) - expected['response'])))
            assert record['independent_edge_max_error'] < 1e-12
        else:
            errors = []
            hermiticity_errors = []
            for momentum in (0.0, case['diagnostics']['minimizer'], np.pi):
                matrix = system.hamiltonian_submatrix(params=dict(params, k_x=momentum), sparse=False)
                hermiticity_errors.append(float(np.max(np.abs(matrix - matrix.conj().T))))
                dense_gap = float(np.min(np.abs(np.linalg.eigvalsh(matrix))))
                sparse_gap = float(np.min(np.abs(source.spectrum(system, dict(params, k_x=momentum), k=4)[0])))
                errors.append(abs(dense_gap - sparse_gap))
                if momentum == case['diagnostics']['minimizer']:
                    record['dense_gap_at_minimum'] = dense_gap
                    assert abs(dense_gap - expected['gap']) < 2e-5
            record.update(dense_sparse_max_error=max(errors), hermiticity_max_error=max(hermiticity_errors))
            assert max(errors) < 1e-8
            assert max(hermiticity_errors) < 1e-12
        records.append(record)
    sample = json.loads((pool / manifest['cases'][0]['request']).read_text())
    truth = json.loads((pool / manifest['cases'][0]['expected']).read_text())
    for malformed in ({}, {'version': 1, 'response': []}, {'version': 1, 'response': [float('nan')] * len(sample['probes'])}):
        try:
            score_result(malformed, truth, sample, 1)
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed result accepted')
    huge = {'version': 1, 'response': [1e308] * len(sample['probes'])}
    assert score_result(huge, truth, sample, 1)[0] == 0
    ablations = {}
    for mode in ('geometry_only', 'gap_only', 'both'):
        baseline = load_source(PILOT / 'participant/workspace/upstream/zigzag.py', PILOT / 'private/reference')
        if mode in ('geometry_only', 'both'):
            method = textwrap.dedent(inspect.getsource(baseline.Shape.edge))
            method = method.replace('return self.shape(site) and any(sites)',
                                    'return not self.shape(site) and any(sites)')
            namespace = dict(baseline.__dict__)
            exec(method, namespace)
            baseline.Shape.edge = namespace['edge']
        if mode in ('gap_only', 'both'):
            baseline.gap_from_band_structure = source.gap_from_band_structure
        grouped = {}
        for case in manifest['cases']:
            request = json.loads((pool / case['request']).read_text())
            expected = json.loads((pool / case['expected']).read_text())
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                result = solve_request(baseline, request)
            score = score_result(result, expected, request, case['weak_rmse'])[0]
            grouped.setdefault(case['family'], []).append(score)
        families = {name: statistics.mean(scores) for name, scores in grouped.items()}
        ablations[mode] = dict(families=families, mean_core_score=statistics.mean(families.values()), worst_family_score=min(families.values()))
    assert ablations['both']['worst_family_score'] > 0.999999
    assert not any((PILOT / 'attempt').iterdir())
    report = dict(status='passed', snapshots_byte_exact=True, license_retained=True,
                  inspected_commits=commits, parsed_python_files=syntax_files,
                  calibrated_weak_score=0.01, reference_checks=records,
                  evaluator_malformed_checks=3, attempt_empty=True, ablations=ablations)
    if arguments.write:
        store_json('private/reference/source_validation.json', report)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()

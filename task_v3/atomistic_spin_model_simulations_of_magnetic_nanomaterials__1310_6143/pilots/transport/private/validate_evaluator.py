import hashlib
import json
import pathlib
import sys
import tempfile
import numpy as np

from metrics import errors, scores, GROUPS

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1]/'authoring'))
from isolated import run_submission


def main():
    manifest = json.loads((ROOT/'private/challenge_pool/manifest.json').read_text())
    first = manifest['splits']['initial'][0]
    expected_path = ROOT/'private/challenge_pool'/first['expected']
    expected = dict(np.load(expected_path, allow_pickle=False))
    zero_error = errors(expected, expected)
    assert all(value == 0.0 for value in zero_error.values())
    calibrations = {group: 1.0 for group in GROUPS}
    assert all(value == 1.0 for value in scores(zero_error, calibrations).values())
    increasing = [scores({group: level for group in GROUPS}, calibrations)['field'] for level in [0.0, 0.1, 0.5, 1.0, 2.0, 4.0]]
    assert all(left > right for left, right in zip(increasing[:-1], increasing[1:]))
    assert scores({group: 1.0 for group in GROUPS}, calibrations)['field'] == 0.5
    invalid_checks = []
    for name, change in [('shape', []), ('nan', float('nan')), ('overflow', 1e308)]:
        broken = dict(expected)
        broken['atom_field_T'] = change if name == 'shape' else np.full(expected['atom_field_T'].shape, change)
        try:
            errors(broken, expected)
        except ValueError:
            invalid_checks.append(name)
        else:
            raise AssertionError(name+' was accepted')
    probe = {'participant_file': str(ROOT/'participant/input/FORMAT.md'), 'forbidden_paths': {'expected_label': str(expected_path), 'manifest': str(ROOT/'private/challenge_pool/manifest.json'), 'reference_source': str(ROOT/'private/reference/upstream/sublattice-resistance.cpp'), 'authoring_notes': str(ROOT.parents[1]/'authoring/candidate_gaps.md'), 'source_checkout': str(ROOT.parents[1]/'authoring/vampire/readme.md')}}
    with tempfile.TemporaryDirectory(prefix='transport-isolation-test-') as scratch:
        scratch = pathlib.Path(scratch)
        case_path = scratch/'case.json'
        output_path = scratch/'output'/'result.json'
        case_path.write_text(json.dumps(probe))
        execution = run_submission(ROOT/'private/security_probe', case_path, output_path, ROOT/'participant', timeout=20, memory_gib=1.0)
        if execution['returncode'] != 0:
            raise AssertionError(execution)
        observed = json.loads(output_path.read_text())
        assert observed['case_readable'] and observed['submission_readable'] and observed['participant_readable']
        assert not any(observed['forbidden_reads'].values()), observed
    provenance = json.loads((ROOT/'private/reference/provenance.json').read_text())
    source_digests = {}
    for source in provenance['sources']:
        if 'sha256' in source:
            path = ROOT/'private/reference/upstream'/pathlib.Path(source['path']).name
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            assert actual == source['sha256']
            source_digests[path.name] = actual
    report = {'passed': True, 'metrics': {'exact_match_score': 1.0, 'weak_normalized_error_score': 0.5, 'strict_monotonicity': increasing, 'invalid_outputs_rejected': invalid_checks}, 'isolation': observed, 'harness': {'path': str(ROOT.parents[1]/'authoring/isolated.py'), 'sha256': hashlib.sha256((ROOT.parents[1]/'authoring/isolated.py').read_bytes()).hexdigest(), 'execution': execution}, 'upstream_source_hashes_verified': source_digests, 'scope': 'Filesystem negative-read smoke test and metric checks; not a comprehensive adversarial sandbox audit.'}
    (ROOT/'private/isolation_validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed': True, 'forbidden_reads': observed['forbidden_reads'], 'metric_checks': invalid_checks}))


if __name__ == '__main__':
    main()

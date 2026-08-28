import argparse
import json
import os
import pathlib
import sys
import tempfile

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]


def probe(arguments):
    forbidden = [ROOT / 'authoring/sources/VASP2KP/README.md', ROOT / 'pilots/04_effective_physics/private/reference/base/bulk_bi2se3_reference.npz', ROOT / 'pilots/04_effective_physics/private/interrupted_initial_attempt/solve.py']
    if pathlib.Path(arguments.input).name.startswith('escape'):
        os.symlink(str(forbidden[1]), arguments.output)
        return
    denied = []
    for path in forbidden:
        try:
            with path.open('rb') as stream:
                stream.read(1)
            denied.append(False)
        except OSError:
            denied.append(True)
    environment_clean = not any('API_KEY' in key or key.startswith('CODEX') or key in ['PYTHONPATH', 'PYTHONHOME'] for key in os.environ)
    np.savez(arguments.output, denied=np.array(denied), environment_clean=np.array(environment_clean), eigenvalues=np.linalg.eigvalsh(np.eye(5)))


def audit():
    sys.path.insert(0, str(ROOT / 'authoring'))
    from sandbox_exec import run_submission
    directory = pathlib.Path(__file__).resolve().parent
    participant = ROOT / 'pilots/04_effective_physics/participant'
    records = {}
    with tempfile.TemporaryDirectory(prefix='task-security-audit-') as temporary:
        temporary = pathlib.Path(temporary)
        for name in ['ordinary', 'escape']:
            input_path = temporary / (name + '.npz')
            np.savez(input_path, probe=np.array(1))
            output_path = temporary / name / 'result.npz'
            result = run_submission(directory / 'solve.py', input_path, output_path, participant)
            if name == 'ordinary' and result['returncode'] == 0:
                with np.load(output_path) as output:
                    result['denied_private_paths'] = output['denied'].tolist()
                    result['environment_clean'] = bool(output['environment_clean'])
                    result['numpy_blas_ok'] = bool(np.array_equal(output['eigenvalues'], np.ones(5)))
            records[name] = result
        entrypoint = temporary / 'entrypoint.py'
        entrypoint.symlink_to(ROOT / 'pilots/04_effective_physics/private/reference/upstream.py')
        records['entrypoint_escape'] = run_submission(entrypoint, input_path, temporary / 'entrypoint_result.npz', participant)
    assert records['ordinary']['returncode'] == 0
    assert all(records['ordinary']['denied_private_paths'])
    assert records['ordinary']['environment_clean'] and records['ordinary']['numpy_blas_ok']
    assert records['escape']['returncode'] == 65
    assert records['entrypoint_escape']['returncode'] == 65
    (ROOT / 'authoring/security_audit.json').write_text(json.dumps(records, indent=2))
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input')
    parser.add_argument('--output')
    parser.add_argument('--audit', action='store_true')
    arguments = parser.parse_args()
    audit() if arguments.audit else probe(arguments)

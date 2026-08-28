import os
import subprocess
import sys
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np

import solve
from validate import FRAMES, check, in_span, row_basis


def main():
    directory = Path(__file__).resolve().parent
    released = directory.parent / 'participant' / 'input'
    for frame in FRAMES:
        inverse = np.array([[frame[1, 1], frame[0, 1]],
                            [frame[1, 0], frame[0, 0]]], dtype=np.uint8)
        assert np.array_equal((frame @ inverse) & 1, np.eye(2, dtype=np.uint8))
    for size in (416, 882):
        example = released / 'examples' / ('smoke_%d.npz' % size)
        destination = directory / ('contract_answer_%d.data' % size)
        subprocess.run([sys.executable, str(directory / 'solve.py'), '--input', str(example),
                        '--output', str(destination)], check=True, timeout=180)
        with np.load(example, allow_pickle=False) as archive:
            case = {key: archive[key] for key in archive.files}
        with np.load(destination, allow_pickle=False) as answer:
            assert set(answer.files) == {'correction_x', 'correction_z'}
            for key in answer.files:
                assert answer[key].shape == (len(case['syndrome']), size)
                assert answer[key].dtype.kind in 'biu'
                assert np.all(answer[key] <= 1)
            actual = (answer['correction_x'] @ case['gz'].T + answer['correction_z'] @ case['gx'].T) & 1
            assert np.array_equal(actual, case['syndrome'])
        destination.unlink()
        hx, hz = case['base_hx'], case['base_hz']
        bases = row_basis(hx), row_basis(hz)
        assert len(bases[0][1]) + len(bases[1][1]) == size - (18 if size == 416 else 24)
        assert in_span(hx, bases[0]).all()
        assert in_span(hz, bases[1]).all()
        reduced, pivots = bases[1]
        logical_found = False
        for column in sorted(set(range(size)) - set(pivots)):
            logical = np.zeros((1, size), dtype=np.uint8)
            logical[0, column] = 1
            logical[0, pivots] = reduced[:, column]
            assert not np.any((logical @ hz.T) & 1)
            if not in_span(logical, bases[0])[0]:
                logical_found = True
                break
        assert logical_found, 'Logical checker must reject some zero-syndrome residuals'
        shots = 3 * size + 1
        errors_x = np.zeros((shots, size), dtype=np.uint8)
        errors_z = np.zeros_like(errors_x)
        for state in (1, 2, 3):
            shot_indices = 1 + (state - 1) * size + np.arange(size)
            errors_x[shot_indices, np.arange(size)] = state & 1
            errors_z[shot_indices, np.arange(size)] = state >> 1
        case['syndrome'] = np.concatenate(((errors_z @ hx.T) & 1, (errors_x @ hz.T) & 1), axis=1)
        correction_x, correction_z = solve.decode(case)
        successes = check(case, correction_x, correction_z, errors_x, errors_z, bases)
        assert successes.all(), ('Single-Pauli logical failure', size, np.flatnonzero(~successes))
        assert not correction_x[0].any() and not correction_z[0].any()
        print('n=%d: CLI schema, all %d single Paulis, zero syndrome, and logical/stabilizer tests passed' %
              (size, 3 * size), flush=True)


if __name__ == '__main__':
    main()

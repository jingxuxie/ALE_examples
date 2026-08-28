import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'authoring'))
from build_v03 import code


def rank(matrix):
    reduced = matrix.copy().astype(np.uint8)
    pivot_row = 0
    for column in range(reduced.shape[1]):
        choices = np.flatnonzero(reduced[pivot_row:, column])
        if not len(choices):
            continue
        selected = pivot_row + int(choices[0])
        reduced[[pivot_row, selected]] = reduced[[selected, pivot_row]]
        following = reduced[pivot_row + 1:]
        following ^= following[:, column, None] * reduced[pivot_row]
        pivot_row += 1
        if pivot_row == len(reduced):
            break
    return pivot_row


def main():
    reports = []
    for length, width in [(6, 6), (12, 6), (9, 6), (12, 12)]:
        matrix, logical, physical, logical_count = code(length, width)
        checks_z = matrix[:physical // 2, :physical]
        checks_x = matrix[physical // 2:, physical:2 * physical]
        zeros = np.zeros_like(checks_x)
        identity = np.eye(physical, dtype=np.uint8)
        harmless = np.block([[checks_x, zeros, zeros], [zeros, zeros, checks_z], [identity, identity, identity]])
        if np.any((matrix @ harmless.T) % 2) or np.any((logical @ harmless.T) % 2):
            raise AssertionError('Observable does not annihilate harmless generators')
        combined_rank = rank(np.vstack([matrix, logical]))
        harmless_rank = rank(harmless)
        if combined_rank + harmless_rank != 3 * physical:
            raise AssertionError('Logical quotient incomplete')
        reports.append({'geometry': [length, width], 'detector_rank': rank(matrix),
                        'detector_logical_rank': combined_rank, 'harmless_rank': harmless_rank,
                        'physical_qubits': physical, 'logical_qubits': logical_count})
    for directory in [ROOT / 'participant/v_03/input', ROOT / 'evaluator/v_03/hidden']:
        for path in directory.glob('*.npz'):
            if path.stem.endswith('_labels'):
                continue
            data = np.load(path, allow_pickle=False)
            labels = np.load(path.with_name(path.stem + '_labels.npz'), allow_pickle=False)
            errors = np.load(ROOT / f'authoring/{path.stem}_physical_replays.npz')['error']
            if not np.isfinite(data['soft_llr']).all():
                raise AssertionError('Nonfinite frontend values')
            if not np.array_equal((errors @ data['H'].T) % 2, data['syndrome']):
                raise AssertionError('Replay syndrome mismatch')
            if not np.array_equal((errors @ data['L'].T) % 2, labels['logical_target']):
                raise AssertionError('Replay logical-label mismatch')
    (ROOT / 'authoring/v03_geometry_checks.json').write_text(json.dumps(reports, indent=2) + '\n')
    print(json.dumps(reports))


if __name__ == '__main__':
    main()

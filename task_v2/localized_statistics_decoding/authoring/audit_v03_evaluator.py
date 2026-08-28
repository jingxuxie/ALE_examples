import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'authoring'))
from build_v03 import nullspace


def main():
    specification = importlib.util.spec_from_file_location('grading_v03', ROOT / 'evaluator/v_03/evaluate.py')
    grading = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(grading)
    data = np.load(ROOT / 'participant/v_03/input/validation_small.npz')
    labels = np.load(ROOT / 'participant/v_03/input/validation_small_labels.npz')
    prediction = np.load(ROOT / 'solution/v_03/validation_small_predictions.npz')['correction']
    count = data['H'].shape[1]

    def unpack(mask):
        return np.asarray([(mask >> index) & 1 for index in range(count)], dtype=np.uint8)

    harmless = unpack(nullspace(np.vstack([data['H'], data['L']]))[0])
    harmful = next(unpack(mask) for mask in nullspace(data['H']) if np.any((data['L'] @ unpack(mask)) % 2))
    equivalent = grading.grade(data, labels, prediction ^ harmless)
    wrong_sector = grading.grade(data, labels, prediction ^ harmful)
    if equivalent['score'] != 1.0 or wrong_sector['score'] != 0.15:
        raise AssertionError((equivalent, wrong_sector))
    result = {'equivalent_nonidentical_corrections': equivalent,
              'syndrome_consistent_wrong_logical_sectors': wrong_sector}
    (ROOT / 'authoring/v03_evaluator_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

import json
import os
from pathlib import Path
import numpy as np


def read(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def metrics(cases, estimates):
    errors = estimates - np.array([case['f'] for case in cases])
    return dict(overall=float(np.sqrt(np.mean(errors ** 2))), **{
        family: float(np.sqrt(np.mean(errors[[case['family'] == family for case in cases]] ** 2)))
        for family in sorted({case['family'] for case in cases})})


def load_data():
    source = Path(os.environ['SRC']) / 'input'
    training = read(source / 'train.jsonl')
    auxiliary = read(source / 'auxiliary_train_L10_L12.jsonl') + read(source / 'auxiliary_validation_L10_L12.jsonl')
    validation = read(source / 'validation.jsonl')
    simulated = read('simulated.jsonl') if Path('simulated.jsonl').exists() else []
    return training, auxiliary, validation, simulated

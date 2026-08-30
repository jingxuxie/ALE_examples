import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from models import load_model, sample_model
from baseline.decoder import Decoder as Baseline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from submission import Decoder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shots', type=int, default=2048)
    parser.add_argument('--seed', type=int, default=728341)
    parser.add_argument('--cases', default='')
    parser.add_argument('--calibration', action='store_true')
    parser.add_argument('--output')
    parser.add_argument('--check-contract', action='store_true')
    args = parser.parse_args()
    participant = Path(os.environ['P'])
    reports = []
    for model_index, path in enumerate(sorted((participant / 'input/cases').iterdir())):
        if args.cases and path.name not in args.cases.split(','):
            continue
        model = load_model(path)
        data_path = ROOT / 'experiments' / f'{path.name}_{args.shots}_{args.seed}.npz'
        if args.calibration:
            data_path = participant / 'input/calibration' / (path.name + '.npz')
        if data_path.exists():
            with np.load(data_path) as data:
                syndromes, labels, baseline = data['syndromes'], data['labels'], data['baseline']
        else:
            syndromes, labels, faults = sample_model(model, args.shots, args.seed + model_index * 100003)
            del faults
            baseline = Baseline(model).decode(syndromes)
            np.savez_compressed(data_path, syndromes=syndromes, labels=labels, baseline=baseline)
        started = time.process_time()
        decoder = Decoder(model)
        saved_syndromes = syndromes.copy() if args.check_contract else None
        predictions = decoder.decode(syndromes)
        elapsed = time.process_time() - started
        assert predictions.shape == labels.shape and predictions.dtype.kind in 'biu'
        assert np.isin(predictions, [0, 1]).all()
        if args.check_contract:
            assert np.array_equal(syndromes, saved_syndromes)
            assert decoder.decode(syndromes[:0]).shape == (0, 4)
            assert np.array_equal(decoder.decode(syndromes[:16][::-1]), predictions[:16][::-1])
            assert np.array_equal(np.concatenate([decoder.decode(syndromes[:7]), decoder.decode(syndromes[7:16])]), predictions[:16])
        wrong_base = np.any(baseline != labels, axis=1)
        wrong = np.any(predictions != labels, axis=1)
        record = dict(case=path.name, shots=len(labels), baseline=int(wrong_base.sum()),
                      failures=int(wrong.sum()), corrected=int((wrong_base & ~wrong).sum()),
                      spoiled=int((~wrong_base & wrong).sum()), seconds=elapsed)
        reports.append(record)
        print(json.dumps(record), flush=True)
        if args.output:
            np.save(ROOT / 'experiments' / f'{args.output}_{path.name}_predictions.npy', predictions)
    print('TOTAL', sum(item['failures'] for item in reports), '/', sum(item['baseline'] for item in reports),
          'CPU', sum(item['seconds'] for item in reports), flush=True)
    shots = sum(item['shots'] for item in reports)
    corrected = sum(item['corrected'] for item in reports)
    spoiled = sum(item['spoiled'] for item in reports)
    improvement = (corrected - spoiled) / shots
    standard_error = np.sqrt(((corrected + spoiled) / shots - improvement ** 2) / shots)
    print('PAIRED_ABSOLUTE_CI95', improvement - 1.96 * standard_error, improvement + 1.96 * standard_error, flush=True)
    if args.output:
        (ROOT / 'experiments' / (args.output + '.json')).write_text(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()

import argparse
import json
import os
import shutil
from pathlib import Path

import numpy as np
import pymatching
import stim

from solve import recover


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', default=os.environ.get('TASK_ROOT'), required=not os.environ.get('TASK_ROOT'))
    parser.add_argument('--shots', type=int, default=50000)
    parser.add_argument('--family', choices=['em3', 'sd6', 'si1000', 'all'], default='all')
    arguments = parser.parse_args()
    root = Path(arguments.task_root)
    families = ['em3', 'sd6', 'si1000'] if arguments.family == 'all' else [arguments.family]
    for family in families:
        source = root / 'input' / ('dev_' + family + '_h')
        request = Path(__file__).parent / 'development_work' / family
        request.mkdir(parents=True, exist_ok=True)
        for name in ['model.dem', 'metadata.json', 'circuit.stim']:
            shutil.copyfile(source / name, request / name)
        circuit = stim.Circuit()
        for instruction in stim.Circuit.from_file(source / 'circuit.stim').flattened():
            circuit.append(instruction.name, instruction.targets_copy(), instruction.gate_args_copy())
        syndrome, truth = circuit.compile_detector_sampler(seed=983714).sample(
            max(100000, arguments.shots), separate_observables=True
        )
        truth = truth[:arguments.shots, 0]
        syndrome = syndrome[:arguments.shots]
        model = stim.DetectorErrorModel.from_file(source / 'model.dem')
        baseline = pymatching.Matching.from_detector_error_model(model, enable_correlations=True)
        reference = baseline.decode_batch(syndrome, enable_correlations=True)[:, 0]
        predictions = np.empty(arguments.shots, dtype=np.uint8)
        for begin in range(0, arguments.shots, 2048):
            batch = syndrome[begin:begin + 2048]
            np.save(request / 'syndromes.npy', batch, allow_pickle=False)
            predictions[begin:begin + len(batch)], _ = recover(request)
        print(json.dumps({
            'family': family, 'shots': arguments.shots,
            'baseline_errors': int(np.sum(reference != truth)),
            'submission_errors': int(np.sum(predictions != truth)),
            'paired_wins': int(np.sum((reference != truth) & (predictions == truth))),
            'paired_losses': int(np.sum((reference == truth) & (predictions != truth))),
        }), flush=True)


if __name__ == '__main__':
    main()

import sys

sys.dont_write_bytecode = True

import os
import time

STARTED = time.monotonic()
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import json
from pathlib import Path

import numpy as np
import stim

from decoder import Decoder
from ensemble import ensemble


def recover(request, budget=54.0, started=None):
    started = time.monotonic() if started is None else started
    deadline = started + budget
    syndromes = np.ascontiguousarray(np.load(request / 'syndromes.npy', allow_pickle=False), dtype=np.uint8)
    if len(syndromes) == 0:
        return np.zeros(0, dtype=np.uint8), {}
    model = stim.DetectorErrorModel.from_file(request / 'model.dem')
    decoder = Decoder(model)
    votes = ensemble(model, syndromes, random_count=16, matching=decoder.baseline,
                     deadline=min(deadline - 3, started + 12))
    baseline = votes[0]
    disagreement = np.sum(votes != baseline, axis=0)
    predictions = baseline ^ (disagreement > (len(votes)+1)/2).astype(np.uint8)
    selected = np.flatnonzero(disagreement)
    random = np.random.default_rng(61451)
    priority = disagreement[selected] + random.random(len(selected)) * .01
    selected = selected[np.argsort(-priority)]
    scores = np.full((len(syndromes), 2), np.inf)
    processed = np.zeros(len(syndromes), dtype=bool)
    metadata_path = request / 'metadata.json'
    style = json.loads(metadata_path.read_text()).get('style', '') if metadata_path.exists() else ''
    mixture = .5 if style == 'SI1000' else 1.0
    batch_size = 8 if decoder.checks <= 800 else 4
    iterations = 20 if decoder.checks <= 400 else 12
    order_count = 400 if decoder.checks <= 400 else 300
    first_count = 0
    second_count = 0
    average_time = 0.01
    for begin in range(0, len(selected), batch_size):
        indices = selected[begin:begin + batch_size]
        if time.monotonic() + max(.25, average_time * len(indices) * 1.6) > deadline:
            break
        start = time.monotonic()
        posterior, converged, _ = decoder.beliefs(syndromes[indices], iterations, 0, 1, 6)
        minimum, evidence = decoder.osd(syndromes[indices], posterior, order_count)
        scores[indices] = (1-mixture) * minimum + mixture * evidence
        predictions[indices] = np.argmin(scores[indices], axis=1)
        processed[indices] = True
        first_count += len(indices)
        elapsed = (time.monotonic() - start) / len(indices)
        average_time = max(elapsed, .7 * average_time + .3 * elapsed)
    gaps = np.full(len(syndromes), np.inf)
    gaps[processed] = np.abs(scores[processed, 0] - scores[processed, 1])
    secondary = np.flatnonzero(processed & (gaps < 8))
    secondary = secondary[np.argsort(gaps[secondary])]
    secondary_order = 600 if decoder.checks <= 400 else 300
    for begin in range(0, len(secondary), batch_size):
        indices = secondary[begin:begin + batch_size]
        if time.monotonic() + max(.3, average_time * len(indices) * 1.8) > deadline:
            break
        start = time.monotonic()
        posterior, converged, _ = decoder.beliefs(syndromes[indices], 20, 0, 1, 4)
        minimum, evidence = decoder.osd(syndromes[indices], posterior, secondary_order)
        scores[indices] = np.minimum(scores[indices], (1-mixture) * minimum + mixture * evidence)
        predictions[indices] = np.argmin(scores[indices], axis=1)
        second_count += len(indices)
        elapsed = (time.monotonic() - start) / len(indices)
        average_time = max(elapsed, .7 * average_time + .3 * elapsed)
    statistics = {'seconds': time.monotonic()-started, 'matching_passes': len(votes),
                  'ambiguous': len(selected), 'first_pass': first_count, 'second_pass': second_count}
    return predictions.astype(np.uint8), statistics


def main():
    request = Path(sys.argv[1])
    prediction, statistics = recover(request, started=STARTED)
    np.save(sys.argv[2], prediction, allow_pickle=False)
    if os.environ.get('DECODER_DIAGNOSTICS'):
        print(json.dumps(statistics), file=sys.stderr)


if __name__ == '__main__':
    main()

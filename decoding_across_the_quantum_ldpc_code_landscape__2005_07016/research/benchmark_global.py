import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research/vendor'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/ale-ldpc-mpl')
import numpy as np
import scipy.sparse as sparse
from ldpc import BpOsdDecoder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', default='pilot')
    parser.add_argument('--shots', type=int, default=12)
    parser.add_argument('--order', type=int, default=8)
    arguments = parser.parse_args()
    pilot = ROOT / 'pilots/01_local_recovery'
    manifest = json.loads((pilot / 'private/reference' / (arguments.split + '_manifest.json')).read_text())
    results = []
    for metadata in manifest:
        case = np.load(pilot / 'private/challenge_pool' / arguments.split / (metadata['name'] + '.npz'))
        reference = np.load(pilot / 'private/reference' / (metadata['name'] + '.npz'))
        parity = sparse.coo_matrix((np.ones(len(case['h_rows']), dtype=np.uint8), (case['h_rows'], case['h_cols'])), shape=tuple(case['h_shape'])).tocsr()
        logical = sparse.coo_matrix((np.ones(len(reference['logical_rows']), dtype=np.uint8), (reference['logical_rows'], reference['logical_cols'])), shape=tuple(reference['logical_shape'])).tocsr()
        print(json.dumps(dict(starting=metadata['name'], order=arguments.order, shots=arguments.shots)), flush=True)
        decoder = BpOsdDecoder(parity, error_channel=case['priors'].tolist(), max_iter=30, bp_method='minimum_sum', ms_scaling_factor=0.625, osd_method='OSD_0' if arguments.order == 0 else 'osd_cs', osd_order=arguments.order)
        syndromes = case['syndromes'][:arguments.shots]
        started = time.perf_counter()
        corrections = np.array([decoder.decode(syndrome).copy() for syndrome in syndromes], dtype=np.uint8)
        elapsed = time.perf_counter() - started
        valid = np.all((parity @ corrections.T).T % 2 == syndromes, axis=1)
        success = valid & np.all((logical @ corrections.T).T % 2 == reference['truth'][:len(syndromes)], axis=1)
        result = dict(name=metadata['name'], shots=len(syndromes), decoder=f'official ldpc 2.4.1 global BP+OSD order {arguments.order}', seconds=elapsed, seconds_per_shot=elapsed / len(syndromes), accuracy=float(success.mean()), validity=float(valid.mean()), dense_matrix_bytes=int(np.prod(case['h_shape'])), caveat='Partial-batch timings are measurements, not a claimed full-batch timeout. This optimized sparse implementation is stronger than a dense generic baseline.')
        results.append(result)
        print(json.dumps(result), flush=True)
        (ROOT / 'research' / f'global_benchmark_{arguments.split}_order{arguments.order}.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

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
from ldpc import BpDecoder

pilot = ROOT / 'pilots/01_local_recovery'
records = json.loads((pilot / 'private/reference/pilot_manifest.json').read_text())
results = []
for schedule, iterations in [('serial', 30), ('serial', 100), ('parallel', 100)]:
    for metadata in records:
        case = np.load(pilot / 'private/challenge_pool/pilot' / (metadata['name'] + '.npz'))
        truth = np.load(pilot / 'private/reference' / (metadata['name'] + '.npz'))
        parity = sparse.coo_matrix((np.ones(len(case['h_rows']), dtype=np.uint8), (case['h_rows'], case['h_cols'])), shape=tuple(case['h_shape'])).tocsr()
        logical = sparse.coo_matrix((np.ones(len(truth['logical_rows']), dtype=np.uint8), (truth['logical_rows'], truth['logical_cols'])), shape=tuple(truth['logical_shape'])).tocsr()
        decoder = BpDecoder(parity, error_channel=case['priors'].tolist(), max_iter=iterations, bp_method='minimum_sum', ms_scaling_factor=0.625, schedule=schedule)
        started = time.process_time()
        corrections = np.array([decoder.decode(syndrome).copy() for syndrome in case['syndromes']], dtype=np.uint8)
        seconds = time.process_time() - started
        valid = np.all((parity @ corrections.T).T % 2 == case['syndromes'], axis=1)
        success = valid & np.all((logical @ corrections.T).T % 2 == truth['truth'], axis=1)
        quality = (float(success.mean()) - metadata['weak_accuracy']) / (metadata['reference_accuracy'] - metadata['weak_accuracy'])
        result = dict(name=metadata['name'], schedule=schedule, iterations=iterations, shots=len(valid), cpu_seconds=seconds, accuracy=float(success.mean()), validity=float(valid.mean()), relative_quality=quality, budget_seconds=metadata['budget_seconds'])
        results.append(result)
        print(json.dumps(result), flush=True)
        (ROOT / 'research/bp_schedule_baselines.json').write_text(json.dumps(results, indent=2))

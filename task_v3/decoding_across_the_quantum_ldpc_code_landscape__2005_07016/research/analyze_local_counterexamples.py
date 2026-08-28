import json
from pathlib import Path
import numpy as np
import scipy.sparse as sparse

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'pilots/01_local_recovery'
report = json.loads((ROOT / 'research/scores/local_challenge.json').read_text())
findings = []
for record in report['cases']:
    name = record['name']
    case = np.load(PILOT / 'private/challenge_pool/challenge' / (name + '.npz'))
    reference = np.load(PILOT / 'private/reference' / (name + '.npz'))
    submitted = np.load(ROOT / 'research/scores/local_challenge_predictions' / (name + '.npz'))['corrections'].astype(np.uint8)
    parity = sparse.coo_matrix((np.ones(len(case['h_rows']), dtype=np.uint8), (case['h_rows'], case['h_cols'])), shape=tuple(case['h_shape'])).tocsr()
    logical = sparse.coo_matrix((np.ones(len(reference['logical_rows']), dtype=np.uint8), (reference['logical_rows'], reference['logical_cols'])), shape=tuple(reference['logical_shape'])).tocsr()
    valid = np.all((parity @ submitted.T).T % 2 == case['syndromes'], axis=1)
    submitted_ok = valid & np.all((logical @ submitted.T).T % 2 == reference['truth'], axis=1)
    reference_ok = np.all((logical @ reference['reference'].T).T % 2 == reference['truth'], axis=1)
    llr = np.log((1 - case['priors']) / case['priors'])
    submitted_cost = submitted @ llr
    reference_cost = reference['reference'] @ llr
    reference_wins = np.flatnonzero(reference_ok & ~submitted_ok)
    submitted_wins = np.flatnonzero(submitted_ok & ~reference_ok)
    counterexamples = []
    for shot in reference_wins:
        difference = reference['reference'][shot] ^ submitted[shot]
        touched = np.asarray(parity[:, np.flatnonzero(difference)].sum(axis=1)).ravel()
        delta = float(submitted_cost[shot] - reference_cost[shot])
        counterexamples.append(dict(shot=int(shot), reference_weight=int(reference['reference'][shot].sum()), submitted_weight=int(submitted[shot].sum()), submitted_minus_reference_cost=delta, likelihood_class='reference_lower_cost' if delta > 1e-8 else ('equal_cost_logical_ambiguity' if abs(delta) <= 1e-8 else 'submission_lower_cost'), difference_weight=int(difference.sum()), touched_checks=int(np.count_nonzero(touched)), logical_disagreements=int(np.count_nonzero(logical @ difference % 2))))
    finding = dict(name=name, family=record['family'], reference_only_successes=len(reference_wins), submission_only_successes=len(submitted_wins), both_fail=int(np.sum(~reference_ok & ~submitted_ok)), invalid_submissions=int(np.sum(~valid)), counterexamples=counterexamples)
    findings.append(finding)
    print(json.dumps(finding), flush=True)
(ROOT / 'research/scores/local_counterexample_audit.json').write_text(json.dumps(findings, indent=2))

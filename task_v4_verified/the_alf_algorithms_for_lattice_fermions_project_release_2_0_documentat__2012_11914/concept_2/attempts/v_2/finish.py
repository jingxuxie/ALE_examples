import json
import subprocess
import sys
import numpy as np
from scipy.special import betaln
from search import ROOT, NAMES, evaluate
from optimize import tensor
from validate import generate

records = json.loads((ROOT / 'assessment.json').read_text())
instances = generate(120, seed=781624)
for filename in ['prob_prunebest_100.json', 'prob_best_90.json', 'prob_more.json']:
    if not (ROOT / filename).exists():
        continue
    artifact = json.loads((ROOT / filename).read_text())
    word = np.array([NAMES.index(stage['component']) for stage in artifact['stages']])
    values = np.array([stage['coefficient'] for stage in artifact['stages']])
    training, _ = evaluate(word, values)
    if training['core'] < 1.8 or training['worst'] < 1.35 or training['max'] > 1:
        print('REJECT', filename, training, flush=True)
        continue
    summary, ratios = evaluate(word, values, instances=instances)
    failure_rates = np.any(ratios > 1, axis=1).reshape(8, -1).mean(axis=1)
    probability = float(np.prod((1 - failure_rates) ** 12))
    records.append((probability, filename, training, summary, failure_rates.tolist()))
    np.savez(ROOT / (filename.replace('.json', '') + '_assessment.npz'), ratios=ratios)
    print('ADDED', records[-1], flush=True)
ranked = []
for record in records:
    filename = record[1]
    ratios = np.load(ROOT / (filename.replace('.json', '') + '_assessment.npz'))['ratios'].reshape(8, -1, 16)
    validation_path = ROOT / (filename.replace('.json', '') + '_validation.npz')
    if validation_path.exists():
        additional = np.load(validation_path)['ratios'].reshape(8, -1, 16)
        ratios = np.concatenate([ratios, additional], axis=1)
    means = np.mean(ratios ** 2, axis=2)
    peaks = np.max(ratios, axis=2)
    rng = np.random.default_rng(914721)
    family_means = []
    maxima = np.zeros(20000)
    for family in range(8):
        indices = rng.integers(ratios.shape[1], size=(20000, 12))
        family_means.append(means[family, indices].mean(axis=1))
        maxima = np.maximum(maxima, peaks[family, indices].max(axis=1))
    family_means = np.array(family_means)
    core = np.exp(-.5 * np.log(family_means).mean(axis=0))
    worst = 1 / np.sqrt(family_means.max(axis=0))
    probability = float(np.mean((maxima <= 1) & (core >= 1.8) & (worst >= 1.35)))
    failures = np.sum(peaks > 1, axis=1)
    successes = ratios.shape[1] - failures
    empirical = float(np.prod((successes / ratios.shape[1]) ** 12))
    predictive = float(np.exp(np.sum(betaln(successes + 12.5, failures + .5) - betaln(successes + .5, failures + .5))))
    probability *= predictive / max(empirical, 1e-12)
    ranked.append((probability, record[3]['core'], filename, record))
ranked.sort(reverse=True)
(ROOT / 'final_selection.json').write_text(json.dumps(ranked, indent=2))
print('FINAL SELECTION', ranked[:5], flush=True)
subprocess.run([sys.executable, str(ROOT / 'finalize.py'), ranked[0][2]], check=True)
subprocess.run([sys.executable, str(ROOT / 'independent_check.py')], check=True)

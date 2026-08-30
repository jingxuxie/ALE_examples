from search import *
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--vertices', action='store_true')
parser.add_argument('--samples', type=int, default=4096)
args = parser.parse_args()
angles = np.array(json.loads((ROOT / 'pulses.json').read_text())['angles']).reshape(48)
random = np.random.default_rng(782348)
errors = stress_set()
random_errors = random.uniform(-1, 1, (args.samples, 15))*np.r_[0.025, 0.025, 0.015, np.full(12,0.005)]
random_errors[:args.samples//2, :3] = np.sign(random_errors[:args.samples//2, :3])*np.array([0.025, 0.025, 0.015])
errors = np.r_[errors, random_errors]
if args.vertices:
    patterns = 0.005*(2*((np.arange(4096)[:, None] >> np.arange(12)) & 1)-1)
    vertices = []
    for common in itertools.product((-0.025,0.025),(-0.025,0.025),(-0.015,0.015)):
        vertices.append(np.c_[np.broadcast_to(common,(4096,3)),patterns])
    errors = np.concatenate([errors] + vertices)
start = time.monotonic()
scores = evaluate(angles, errors)[0]
worst = np.argsort(scores)[:64]
exact_indices = np.unique(np.r_[np.arange(len(stress_set())),worst, random.choice(len(errors),32,replace=False)])
exact_scores = fidelities(angles.reshape(24,2), scenarios_from_errors(errors[exact_indices]))
print('SCENARIOS',len(errors),'MINIMUM',scores.min(),'MEAN',scores.mean(),'TIME',time.monotonic()-start,flush=True)
print('EXACT MINIMUM',exact_scores.min(),'MAX DISCREPANCY',abs(exact_scores-scores[exact_indices]).max(),flush=True)
print('WORST SCENARIO',errors[worst[0]].tolist(),flush=True)
np.save(ROOT/'validation_errors.npy', errors)
np.save(ROOT/'validation_scores.npy', scores)
np.save(ROOT/'worst_errors.npy', errors[worst])
report = dict(scenario_count=len(errors),minimum_fidelity=float(scores.min()),mean_fidelity=float(scores.mean()),
              exact_check_count=len(exact_indices), exact_minimum=float(exact_scores.min()),
              maximum_fast_exact_discrepancy=float(abs(exact_scores-scores[exact_indices]).max()),
              worst_scenario=errors[worst[0]].tolist(),
              public_fidelities=fidelities(angles.reshape(24,2),training_scenarios()).tolist(),
              exact_checked_scenarios=scenarios_from_errors(errors[exact_indices]),
              exact_fidelities=exact_scores.tolist())
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')

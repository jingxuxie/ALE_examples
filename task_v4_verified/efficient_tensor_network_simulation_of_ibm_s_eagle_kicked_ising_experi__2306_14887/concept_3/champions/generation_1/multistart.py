from search import *

random = np.random.default_rng(1488731)
errors = stress_set()
best = np.array(json.loads((ROOT / 'pulses.json').read_text())['angles']).reshape(48)
best_score = evaluate(best, errors)[0].min()
baseline = np.array(json.loads((ASSETS / 'baseline' / 'pulses.json').read_text())['angles']).reshape(48)
bank = [best.copy(), baseline.copy()]
start = time.monotonic()
for trial in range(120):
    if trial % 10 == 9:
        initial = np.repeat(random.uniform(-np.pi, np.pi, 24), 2)
        initial = optimize(initial, np.zeros((1,15)), 0, 800, global_only=True, label=f'nominal {trial}')
    else:
        source = bank[random.integers(len(bank))] if trial % 3 else best
        initial = source.reshape(24, 2).copy()
        selected = random.random(24) < (0.15 if trial % 2 else 0.5)
        initial[selected] += np.pi
        initial = (initial+np.pi)%(2*np.pi)-np.pi
        if trial % 4 == 3:
            initial += random.normal(0, 0.15, (24, 2))
            initial = np.clip(initial, -np.pi, np.pi)
    candidate = optimize(initial, errors, 0.003, 900, label=f'trial {trial}')
    scores = evaluate(candidate, errors)[0]
    if scores.min() > best_score-0.015:
        bank.append(candidate.copy())
    if scores.min() > best_score:
        candidate = optimize(candidate, errors, 0.0003, 500, label=f'polish {trial}')
        scores = evaluate(candidate, errors)[0]
        best_score = scores.min()
        best = candidate
        save_pulses(ROOT, best.reshape(24,2))
        np.save(ROOT / f'best_trial_{trial}.npy', best)
        print('NEW BEST', trial, best_score, 'elapsed', time.monotonic()-start, flush=True)
    print('TRIAL RESULT', trial, scores.min(), 'BEST', best_score, 'elapsed', time.monotonic()-start, flush=True)
    if best_score > 0.98:
        break

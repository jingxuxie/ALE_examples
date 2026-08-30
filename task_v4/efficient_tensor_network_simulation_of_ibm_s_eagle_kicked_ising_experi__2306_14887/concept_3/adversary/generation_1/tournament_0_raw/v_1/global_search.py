from search import *

random = np.random.default_rng(634593)
full_errors = stress_set()
errors = np.array([np.r_[gain_a, gain_b, common, np.full(12,np.sign(common)*0.005)]
                   for gain_a,gain_b,common in itertools.product((-0.025,0.025),(-0.025,0.025),(-0.015,0.015))])
best = np.array(json.loads((ROOT/'pulses.json').read_text())['angles']).reshape(48)
best_score = evaluate(best,full_errors)[0].min()
start = time.monotonic()
for trial in range(300):
    if trial % 5 == 4:
        initial = best.reshape(24,2).mean(axis=1)+random.normal(0,0.5,24)
        initial = np.repeat(np.clip(initial,-np.pi,np.pi),2)
    else:
        initial = np.repeat(random.uniform(-np.pi/2,np.pi/2,24),2)
    initial = optimize(initial,np.zeros((1,15)),0,300,global_only=True,label=f'nominal {trial}')
    if trial % 3 != 0:
        initial = (initial+np.pi/2)%np.pi-np.pi/2
    candidate = optimize(initial,errors,0.002,900,global_only=True,label=f'global {trial}')
    scores = evaluate(candidate,full_errors)[0]
    if scores.min() > best_score-0.004:
        candidate = optimize(candidate,full_errors,0.0003,700,label=f'full polish {trial}')
        scores = evaluate(candidate,full_errors)[0]
    if scores.min() > best_score:
        best_score = scores.min()
        best = candidate.copy()
        save_pulses(ROOT,best.reshape(24,2))
        np.save(ROOT/f'global_best_{trial}.npy',best)
        print('NEW BEST',trial,best_score,'elapsed',time.monotonic()-start,flush=True)
    print('TRIAL RESULT',trial,scores.min(),'BEST',best_score,'elapsed',time.monotonic()-start,flush=True)
    if best_score>0.98:
        break

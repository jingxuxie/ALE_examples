import argparse
import time
import numpy as np
import fermion
from search import Engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--beam', type=int, default=80)
    parser.add_argument('--choices', type=int, default=10)
    parser.add_argument('--seed', type=int, default=22)
    parser.add_argument('--random', type=int, default=0)
    parser.add_argument('--phase', type=int, default=1)
    parser.add_argument('--projected', action='store_true')
    parser.add_argument('--entropy', type=float, default=0.0)
    parser.add_argument('--power', type=float, default=1.0)
    parser.add_argument('--noise', type=float, default=0.0)
    parser.add_argument('--tag', default='')
    args = parser.parse_args()
    engine = Engine(fermion.load_cases()[args.case])
    engine.best = engine.load()[2]
    engine.target = engine.target * args.phase
    rng = np.random.default_rng(args.seed)
    original_target=engine.target.copy()
    if args.power!=1.0 or args.noise:
        engine.target=np.sign(original_target)*np.abs(original_target)**args.power+rng.normal(0,args.noise,len(original_target))
        engine.target/=np.linalg.norm(engine.target)
    beam = [(np.empty(0, np.int32), np.empty(0), 2 - 2 * (engine.initial @ engine.target))]
    for step in range(engine.case.max_gates):
        trials = []
        for labels, angles, loss in beam:
            values, optimal = engine.projected(labels, angles) if args.projected and step > 1 else engine.options(labels, angles)
            order = np.argsort(values.ravel())[::-1]
            if step == 0:
                selected = order
            elif args.random:
                selected = rng.choice(order[:max(args.choices, args.random)], args.choices, replace=False)
            else:
                selected = order
            fingerprints = set()
            for flat in selected:
                position, label = np.unravel_index(flat, values.shape)
                trial_labels = np.insert(labels, position, label)
                trial_angles = np.insert(angles, position, optimal[position, label])
                trial_labels, trial_angles, trial_loss = engine.optimize(trial_labels, trial_angles, 100)
                state, _ = engine.state_jac(trial_labels, trial_angles)
                fingerprint = np.round(state, 5).tobytes()
                if fingerprint not in fingerprints:
                    trials.append((trial_labels, trial_angles, trial_loss, state))
                    fingerprints.add(fingerprint)
                if step > 0 and len(fingerprints) >= args.choices:
                    break
        entropy_weight=args.entropy*min(1.0,(engine.case.max_gates-step-1)/8)
        trials.sort(key=lambda trial: trial[2]+entropy_weight*np.sum(trial[3]**2*np.log(trial[3]**2+1e-100)))
        kept = []
        fingerprints = set()
        for trial_labels, trial_angles, trial_loss, state in trials:
            fingerprint = np.round(state, 4).tobytes()
            if fingerprint in fingerprints:
                continue
            if kept and max(abs(state @ old[3]) for old in kept) > 1 - 1e-7:
                continue
            kept.append((trial_labels, trial_angles, trial_loss, state))
            fingerprints.add(fingerprint)
            if len(kept) >= args.beam:
                break
        beam = [(labels, angles, loss) for labels, angles, loss, state in kept]
        print('beam',step+1,'states',len(beam),'best',beam[0][2],'worst',beam[-1][2],'elapsed',time.time()-engine.started,flush=True)
    engine.target=original_target
    beam=[engine.optimize(labels,angles,300) for labels,angles,loss in beam]
    beam.sort(key=lambda trial:trial[2])
    for labels, angles, loss in beam:
        engine.save(labels, angles, loss)
    for position, (labels, angles, loss) in enumerate(beam):
        engine.save(labels, angles, loss, 'beam_' + (args.tag + '_' if args.tag else '') + str(position))
    for labels, angles, loss in beam[:10]:
        labels, angles, loss = engine.polish(labels, angles, loss, rounds=10, width=50)
        engine.save(labels, angles, loss)


if __name__ == '__main__':
    main()

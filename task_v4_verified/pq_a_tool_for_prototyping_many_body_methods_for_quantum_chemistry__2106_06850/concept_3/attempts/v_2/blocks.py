import argparse
import ctypes
import itertools
import time
import numpy as np
import fermion
from search import Engine, LIB, INT, DOUBLE


LIB.block_bases.argtypes = [ctypes.c_int, INT, DOUBLE, DOUBLE, DOUBLE, ctypes.c_int, ctypes.c_int, DOUBLE, DOUBLE]
LIB.block_maxima.argtypes = [DOUBLE, DOUBLE, DOUBLE, DOUBLE]


def options(engine, labels, angles, first, second):
    left, right = np.empty((750,100)), np.empty((750,100))
    LIB.block_bases(len(labels),labels,angles,engine.initial,engine.target,first,second,left,right)
    matrix = np.ascontiguousarray(left @ right.T)
    values, first_angles, second_angles = np.empty((250,250)), np.empty((250,250)), np.empty((250,250))
    LIB.block_maxima(matrix, values, first_angles, second_angles)
    return values, first_angles, second_angles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--choices', type=int, default=30)
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    engine = Engine(fermion.load_cases()[args.case])
    labels, angles, loss = engine.load()
    engine.best = loss
    rng = np.random.default_rng(982)
    iteration = 0
    while time.time() - engine.started < args.seconds:
        iteration += 1
        pairs = list(itertools.combinations(range(len(labels)),2)) if args.all else [(position,position+1) for position in range(len(labels)-1)]
        rng.shuffle(pairs)
        initial_loss = loss
        for first, second in pairs:
            values, first_angles, second_angles = options(engine, labels, angles, first, second)
            values[labels[first],labels[second]] = -np.inf
            order = np.argsort(values.ravel())[::-1]
            trials, fingerprints = [], set()
            for flat in order:
                first_label, second_label = np.unravel_index(flat, values.shape)
                trial_labels, trial_angles = labels.copy(), angles.copy()
                trial_labels[first], trial_labels[second] = first_label, second_label
                trial_angles[first],trial_angles[second] = first_angles[first_label,second_label],second_angles[first_label,second_label]
                trial_state, _ = engine.state_jac(trial_labels, trial_angles)
                fingerprint = np.round(trial_state, 6).tobytes()
                if fingerprint in fingerprints:
                    continue
                fingerprints.add(fingerprint)
                trials.append(engine.optimize(trial_labels,trial_angles,200))
                if len(trials)>=args.choices:
                    break
            candidate = min(trials,key=lambda item:item[2])
            if candidate[2]<loss-1e-11:
                labels,angles,loss=candidate
                engine.save(labels,angles,loss)
            if time.time()-engine.started>=args.seconds:
                break
        print('block sweep',iteration,'loss',loss,'elapsed',time.time()-engine.started,flush=True)
        if loss>=initial_loss-1e-11:
            break


if __name__=='__main__':
    main()

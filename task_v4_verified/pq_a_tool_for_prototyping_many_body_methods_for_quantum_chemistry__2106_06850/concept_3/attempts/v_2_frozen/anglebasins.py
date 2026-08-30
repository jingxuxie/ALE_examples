import argparse
import time
import numpy as np
import fermion
from search import Engine


parser = argparse.ArgumentParser()
parser.add_argument('--case', type=int, default=0)
parser.add_argument('--seconds', type=float, default=120)
args = parser.parse_args()
engine = Engine(fermion.load_cases()[args.case])
labels, angles, loss = engine.load()
engine.best = loss
rng = np.random.default_rng(987)
iteration = 0
while time.time() - engine.started < args.seconds:
    iteration += 1
    perturbed = angles.copy()
    positions = rng.choice(len(labels), int(rng.integers(1, len(labels)+1)), replace=False)
    perturbed[positions] += rng.normal(0, rng.choice([0.3, 0.8, 1.5, 3.0]), len(positions))
    result = engine.optimize(labels, perturbed, 400)
    if result[2] < loss - 1e-12:
        labels, angles, loss = result
        engine.save(labels, angles, loss)
    if iteration % 200 == 0:
        print('iteration',iteration,'best',loss,'elapsed',time.time()-engine.started,flush=True)

import argparse
import time
import numpy as np
import fermion
from search import Engine


parser = argparse.ArgumentParser()
parser.add_argument('--case', type=int, default=0)
args = parser.parse_args()
engine = Engine(fermion.load_cases()[args.case])
rng = np.random.default_rng(71)
reference = engine.case.reference_mask
occupied = set(orbital for orbital in range(10) if reference >> orbital & 1)
virtual = set(range(10)) - occupied
pool = np.array([position for position, label in enumerate(engine.labels) if set(label.annihilate) <= occupied and set(label.create) <= virtual or set(label.create) <= occupied and set(label.annihilate) <= virtual], np.int32)
print('pool',len(pool),pool,flush=True)
for layout in range(4):
    labels = pool.copy()
    if layout == 1:
        labels = labels[::-1].copy()
    elif layout == 2:
        labels = np.roll(labels, -12)
    elif layout == 3:
        rng.shuffle(labels)
    best = 1.0
    for repeat in range(15):
        angles = rng.normal(scale=0.3 if repeat < 5 else 1.0, size=len(labels))
        found_labels, found_angles, loss = engine.optimize(labels, angles, 800)
        if loss < best:
            best = loss
            print('layout',layout,'restart',repeat,'loss',loss,'small',sum(abs(found_angles)<1e-5),'elapsed',time.time()-engine.started,flush=True)
            engine.save(found_labels, found_angles, loss, 'template'+str(layout))

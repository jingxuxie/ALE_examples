import time
import numpy as np
from pathlib import Path
import finite
from finite_implicit import optimize
from promote import promote

initial='finite_implicit_1.npz' if Path('finite_implicit_1.npz').exists() else 'finite_implicit_0.npz'
current=np.load(initial)['variables']
started=time.time()
trust=.08
for number in range(8):
    label=f'tight{number}'
    candidate=optimize(current,label,750,trust)
    values=np.asarray(finite.outputs(candidate))
    if max(abs(values[1:19]))<1e-8 and min(values[19:])>-.001:
        current=candidate
        promote(f'finite_implicit_{label}.json')
    else:
        trust*=.7
    if time.time()-started>650:break

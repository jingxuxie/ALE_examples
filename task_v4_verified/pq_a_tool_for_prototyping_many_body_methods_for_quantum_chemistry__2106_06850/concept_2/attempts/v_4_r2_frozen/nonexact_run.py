import time
import json
import numpy as np
from pathlib import Path
import finite
import search as engine
from finite_implicit import optimize
from promote import promote

original_outputs=finite.outputs
original_jacobian=finite.jacobian
finite.outputs=lambda current:original_outputs(current,.000995)
finite.jacobian=lambda current:original_jacobian(current,.000995)
source=json.loads(Path('least_second.json').read_text())
coordinates=np.einsum('kij,ij->k',engine.axes,np.array(source['pair_matrix']))
current=np.r_[coordinates,source['amplitudes']]
started=time.time()
for number in range(4):
    label=f'nonexact{number}'
    candidate=optimize(current,label,900,.15)
    values=np.asarray(finite.outputs(candidate))
    if max(abs(values[1:19]))<1e-8 and min(values[19:])>-.001:
        current=candidate
        promote(f'finite_implicit_{label}.json')
    if time.time()-started>420:break

import json
import numpy as np
from pathlib import Path
import finite
import search as engine
from finite_implicit import optimize
from promote import promote

finite.EXTRA_AXES=((92,1),(92,-1))
source=json.loads(Path('submission.json').read_text())
coordinates=np.einsum('kij,ij->k',engine.axes,np.array(source['pair_matrix']))
current=np.r_[coordinates,source['amplitudes']]
candidate=optimize(current,'worst',650,.06)
values=np.asarray(finite.outputs(candidate))
if max(abs(values[1:19]))<1e-8 and min(values[19:])>-.001:
    promote('finite_implicit_worst.json')

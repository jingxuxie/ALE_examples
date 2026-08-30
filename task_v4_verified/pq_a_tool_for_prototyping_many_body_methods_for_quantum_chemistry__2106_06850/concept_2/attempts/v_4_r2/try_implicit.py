import implicit
import search as engine
import numpy as np
import json
from pathlib import Path

for number,filename in enumerate(['least_second.json','quiet_path7.json']):
    data=json.loads(Path(filename).read_text())
    coordinates=np.einsum('kij,ij->k',engine.axes,np.array(data['pair_matrix']))
    current=np.r_[coordinates,data['amplitudes']]
    current=implicit.optimize(current,np.array([0.,1.,.097,.00008,.001]),f'retry{number}',1200,trust=.2)

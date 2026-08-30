import refine
import quiet
import search as engine
import numpy as np

initials=np.load('samples.npz')['variables'][:15].copy()
for number,initial in enumerate(initials):
    current=refine.refine(initial,np.array([10.,0.,0.,1.,1.,.024]),f'multi{number}a',500)
    values=np.asarray(engine.metrics(current))
    if values[13]>1e-7 or abs(values[2])>1e-7:
        continue
    limit=min(values[3]*.8,.5)
    for stage in range(8):
        limit=max(limit,.094)
        current=quiet.optimize(current,np.array([0.,1.,limit,.00001]),f'multi{number}q{stage}',500,trust=.22)
        if limit<=.094:
            break
        limit*=.72

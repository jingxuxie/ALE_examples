import implicit
import numpy as np
import search as engine

current=np.load('polished_retry.npz')['variables']
for number in range(12):
    candidate=implicit.optimize(current,np.array([0.,1.,.097,.00006,.004]),f'stable{number}',1000,trust=.12)
    values=np.asarray(engine.metrics(candidate[:138]))
    if abs(values[2])<1e-5 and values[13]<1e-7 and values[4]>.999 and values[3]<.100:
        current=candidate

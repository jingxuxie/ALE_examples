import quiet
import numpy as np
current=np.load('refine_0a.npz')['variables']
for number,limit in enumerate([.28,.25,.22,.19,.16,.13,.11,.095]):
    current=quiet.optimize(current,np.array([0.,1.,limit,.0001]),f'path{number}',700,trust=.18)

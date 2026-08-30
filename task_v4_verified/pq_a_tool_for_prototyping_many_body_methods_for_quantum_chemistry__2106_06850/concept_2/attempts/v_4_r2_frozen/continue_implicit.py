import implicit
import numpy as np
current=np.load('implicit_retry1.npz')['variables']
for number in range(8):
    current=implicit.optimize(current,np.array([0.,1.,.097,.00005,.004]),f'continue{number}',1200,trust=.3)

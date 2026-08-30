import time
import numpy as np
from multiprocessing import Pool
import meanfield_features

def work(arguments):
    return meanfield_features.calculate(*arguments)

if __name__=='__main__':
    for split in ('train','validation'):
        data=dict(np.load('dev/'+split+'.npz'))
        jobs=[(data['hopping'][index,:sites,:sites],data['interaction'][index,:sites],data['potential'][index,:sites]) for index,sites in enumerate(data['n_sites'])]
        started=time.perf_counter()
        with Pool(4) as pool:
            result=list(pool.imap(work,jobs))
        np.save('dev/'+split+'_meanfield.npy',result)
        print(split,'finished',time.perf_counter()-started,flush=True)

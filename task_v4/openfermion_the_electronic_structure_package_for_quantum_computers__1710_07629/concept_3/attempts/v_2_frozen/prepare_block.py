import time
import numpy as np
from multiprocessing import Pool
import block_features

def work(arguments):
    return block_features.calculate(*arguments)

if __name__=='__main__':
    for split in ('train','validation'):
        data=dict(np.load('dev/'+split+'.npz'))
        jobs=[(data['hopping'][index,:sites,:sites],data['interaction'][index,:sites],data['potential'][index,:sites]) for index,sites in enumerate(data['n_sites'])]
        started=time.perf_counter()
        result=[]
        with Pool(4) as pool:
            for index,values in enumerate(pool.imap(work,jobs)):
                result.append(values)
                if index%100==0:
                    print(split,index,time.perf_counter()-started,flush=True)
        np.save('dev/'+split+'_block.npy',result)
        print(split,'finished',time.perf_counter()-started,flush=True)

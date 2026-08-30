import argparse
import time
from pathlib import Path
from multiprocessing import Pool
import numpy as np
import block_features

def work(arguments):
    return block_features.calculate_perturb(*arguments)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('datasets',nargs='+')
    parser.add_argument('--workers',type=int,default=2)
    arguments=parser.parse_args()
    for split in arguments.datasets:
        data=dict(np.load('dev/'+split+'.npz'))
        path=Path('dev/'+split+'_perturb.npy')
        result=list(np.load(path)) if path.exists() else []
        jobs=[(data['hopping'][index,:sites,:sites],data['interaction'][index,:sites],data['potential'][index,:sites]) for index,sites in enumerate(data['n_sites']) if index>=len(result)]
        started=time.perf_counter()
        with Pool(arguments.workers) as pool:
            for values in pool.imap(work,jobs):
                result.append(values)
                if len(result)%128==0:
                    np.save(path,result)
                    print(split,len(result),time.perf_counter()-started,flush=True)
        np.save(path,result)
        print(split,'finished',len(result),time.perf_counter()-started,flush=True)

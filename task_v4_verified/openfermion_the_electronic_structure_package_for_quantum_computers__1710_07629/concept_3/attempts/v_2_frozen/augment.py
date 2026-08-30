import argparse
import time
from multiprocessing import Pool
import numpy as np
import distribution
import exact_labels
import baseline_features
import physics_features
import active_features
import block_features
import meanfield_features

def work(arguments):
    hopping,interaction,potential=arguments
    labels=exact_labels.predict_instance(hopping,interaction,potential)
    physics=physics_features.calculate(hopping,interaction,potential)
    active=active_features.calculate(hopping,interaction,potential)
    block=block_features.calculate(hopping,interaction,potential)
    meanfield=meanfield_features.calculate(hopping,interaction,potential)
    return labels,physics,active,block,meanfield

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--count',type=int,default=192)
    parser.add_argument('--seed',type=int,default=2835912)
    parser.add_argument('--output',default='extra')
    arguments=parser.parse_args()
    data=distribution.draw_batch(arguments.count,arguments.seed)
    jobs=[(np.ascontiguousarray(data['hopping'][index,:sites,:sites]),np.ascontiguousarray(data['interaction'][index,:sites]),np.ascontiguousarray(data['potential'][index,:sites])) for index,sites in enumerate(data['n_sites'])]
    result=[]
    started=time.perf_counter()
    with Pool(4) as pool:
        for index,values in enumerate(pool.imap(work,jobs)):
            result.append(values)
            if index%32==31 or index+1==len(jobs):
                saved={key:value[:index+1] for key,value in data.items()}
                saved['gaps']=np.asarray([row[0] for row in result])
                np.savez_compressed('dev/'+arguments.output+'.npz',**saved)
                features={'basic':baseline_features.features(saved)}
                for column,name in enumerate(('physics','active','block','meanfield')):
                    features[name]=np.asarray([row[column+1] for row in result])
                np.savez_compressed('dev/'+arguments.output+'_features.npz',**features)
                print(index+1,len(jobs),time.perf_counter()-started,flush=True)

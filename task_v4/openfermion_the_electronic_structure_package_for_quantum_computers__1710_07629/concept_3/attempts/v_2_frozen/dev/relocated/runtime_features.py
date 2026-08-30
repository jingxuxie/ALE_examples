import numpy as np
import baseline_features
import geometry_features
import physics_features
import active_features
import block_features

def features(inputs,mode):
    basic=baseline_features.features(inputs)
    geometry=geometry_features.features(inputs)
    rows=[]
    for index,sites in enumerate(inputs['n_sites']):
        hopping=np.ascontiguousarray(inputs['hopping'][index,:sites,:sites])
        interaction=np.ascontiguousarray(inputs['interaction'][index,:sites])
        potential=np.ascontiguousarray(inputs['potential'][index,:sites])
        arguments=(hopping,interaction,potential)
        factors=(1.,) if mode.endswith('fast') else (1.,1.5)
        physical=np.asarray(physics_features.calculate(*arguments,factors=factors))
        if len(factors)==1:
            physical=np.r_[physical[:5],np.zeros(5),physical[5:]]
        counts=(4,6) if mode in ('lean','leanfast') else (4,)
        active=np.asarray(active_features.calculate(*arguments,counts=counts))
        if len(counts)==1:
            active=np.r_[active,np.zeros(5)]
        if mode.startswith('perturb'):
            perturb=np.asarray(block_features.calculate_perturb(*arguments))
            block=np.r_[perturb[:6],np.zeros(5)]
        else:
            block=np.r_[block_features.calculate(*arguments,counts=(4,)),np.zeros(5)]
            perturb=np.zeros(20)
        rows.append(np.r_[basic[index],physical,active,block,np.zeros(17),geometry[index],perturb])
    return np.asarray(rows)

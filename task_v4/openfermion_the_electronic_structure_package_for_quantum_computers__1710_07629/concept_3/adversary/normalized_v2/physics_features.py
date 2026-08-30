import ctypes
from pathlib import Path
import numpy as np

LIBRARY = ctypes.CDLL(str(Path(__file__).resolve().with_name('physics.so')))
POINTER = ctypes.POINTER(ctypes.c_double)
LIBRARY.tj_energy.argtypes = [ctypes.c_int]*3+[POINTER]*3+[ctypes.c_int]
LIBRARY.tj_energy.restype = ctypes.c_double

def ptr(array):
    return array.ctypes.data_as(POINTER)

def tj_energy(hopping, exchange, onsite, holes, up, steps=80):
    return LIBRARY.tj_energy(len(onsite), holes, up, ptr(hopping), ptr(exchange), ptr(onsite), steps)

def calculate(hopping, interaction, potential, factors=(1.0,1.5)):
    sites = len(interaction)
    half = sites//2
    mean_u = np.mean(interaction)
    differences = potential[:,None]-potential[None,:]
    denominators = interaction[:,None]+differences
    first,second = np.where(np.triu(hopping != 0,1))
    dimers = np.zeros((len(first),3,3))
    dimers[:,1,1] = denominators[first,second]
    dimers[:,2,2] = denominators[second,first]
    dimers[:,0,1] = dimers[:,1,0] = -np.sqrt(2)*hopping[first,second]
    dimers[:,0,2] = dimers[:,2,0] = -np.sqrt(2)*hopping[first,second]
    exchange = np.zeros_like(hopping)
    exchange[first,second] = -np.linalg.eigvalsh(dimers)[:,0]
    exchange += exchange.T
    zeros = np.zeros(sites)
    negative = np.ascontiguousarray(-hopping)
    removed = np.ascontiguousarray(-potential)
    added = np.ascontiguousarray(potential+interaction-mean_u)
    result = []
    for factor in factors:
        coupling = exchange*factor
        if result and factors[0]==1.0:
            neutral=result[0]*factor
            spin=(result[0]+result[1])*factor
        else:
            neutral = tj_energy(hopping,coupling,zeros,0,half)
            spin = tj_energy(hopping,coupling,zeros,0,half+1)
        hole = tj_energy(hopping,coupling,removed,1,half)
        electron = tj_energy(negative,coupling,added,1,half)
        result.extend([neutral,spin-neutral,hole-neutral,electron-neutral,mean_u+hole+electron-2*neutral])
    result.extend([np.mean(exchange[first,second]),np.std(exchange[first,second])])
    return result

def features(inputs):
    return np.array([calculate(np.ascontiguousarray(inputs['hopping'][index,:sites,:sites]),
                              np.ascontiguousarray(inputs['interaction'][index,:sites]),
                              np.ascontiguousarray(inputs['potential'][index,:sites]))
                     for index, sites in enumerate(inputs['n_sites'])])

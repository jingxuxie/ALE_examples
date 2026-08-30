import ctypes
from functools import lru_cache
import itertools
from pathlib import Path
import numpy as np

LIBRARY=ctypes.CDLL(str(Path(__file__).resolve().with_name('krylov.so')))
POINTER=ctypes.POINTER(ctypes.c_double)
LIBRARY.ground_energy.argtypes=[ctypes.c_int]*3+[POINTER]*5+[ctypes.c_int,ctypes.c_double,POINTER]
LIBRARY.ground_energy.restype=ctypes.c_double

def ptr(array):
    return array.ctypes.data_as(POINTER)

@lru_cache(None)
def occupations(sites,particles):
    combinations=itertools.combinations(range(sites),particles)
    return np.array(sorted(combinations,key=lambda occupied:sum(1<<site for site in occupied)))

def calculate(hopping,interaction,potential,steps=12):
    sites=len(interaction)
    half=sites//2
    hopping=np.ascontiguousarray(hopping)
    interaction=np.ascontiguousarray(interaction)
    potential=np.ascontiguousarray(potential)
    one_body=-hopping+np.diag(potential+0.5*(interaction-np.mean(interaction)))
    _,orbitals=np.linalg.eigh(one_body)
    trials={particles:np.ascontiguousarray(np.linalg.det(orbitals[occupations(sites,particles),:particles])) for particles in (half-1,half,half+1)}
    histories=[]
    for up,down in [(half,half),(half+1,half-1),(half+1,half),(half,half-1)]:
        history=np.zeros(steps)
        energy=LIBRARY.ground_energy(sites,up,down,ptr(hopping),ptr(interaction),ptr(potential),ptr(trials[up]),ptr(trials[down]),steps,0.,ptr(history))
        histories.append(history[1::2])
    histories=np.array(histories)
    result=np.stack([histories[2]+histories[3]-2*histories[0],histories[1]-histories[0],histories[0],histories[2]-histories[0],histories[0]-histories[3]],axis=1)
    return result.ravel()

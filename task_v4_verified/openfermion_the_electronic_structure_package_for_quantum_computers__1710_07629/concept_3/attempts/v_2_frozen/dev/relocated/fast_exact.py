import numpy as np
import ctypes
from exact_labels import LIBRARY,pointer,occupations

LIBRARY.set_limits.argtypes=[ctypes.c_double,ctypes.c_double]
LIBRARY.timed_out.restype=ctypes.c_int

def calculate(hopping,interaction,potential,steps=80):
    sites=len(interaction)
    half=sites//2
    hopping=np.ascontiguousarray(hopping)
    interaction=np.ascontiguousarray(interaction)
    potential=np.ascontiguousarray(potential)
    one_body=-hopping+np.diag(potential+0.5*(interaction-np.mean(interaction)))
    _,orbitals=np.linalg.eigh(one_body)
    trials={particles:np.ascontiguousarray(np.linalg.det(orbitals[occupations(sites,particles),:particles])) for particles in (half-1,half,half+1)}
    energies=[]
    for up,down in [(half,half),(half+1,half-1),(half+1,half),(half,half-1)]:
        energies.append(LIBRARY.ground_energy(sites,up,down,pointer(hopping),pointer(interaction),pointer(potential),pointer(trials[up]),pointer(trials[down]),steps,1e-6,None))
    neutral=min(energies[:2])
    return [energies[2]+energies[3]-2*neutral,energies[1]-neutral]

from functools import lru_cache
import itertools
import numpy as np
from scipy.sparse.linalg import eigsh
from native_eigh import lowest

@lru_cache(None)
def operators(orbitals,particles):
    masks = [mask for mask in range(1<<orbitals) if mask.bit_count()==particles]
    lookup = {mask:index for index,mask in enumerate(masks)}
    result = np.zeros((orbitals,orbitals,len(masks),len(masks)))
    for column,mask in enumerate(masks):
        for source in range(orbitals):
            if not (mask>>source)&1:
                continue
            intermediate = mask^(1<<source)
            source_sign = (-1)**((mask&((1<<source)-1)).bit_count())
            for destination in range(orbitals):
                if (intermediate>>destination)&1:
                    continue
                row = lookup[intermediate|(1<<destination)]
                sign = source_sign*(-1)**((intermediate&((1<<destination)-1)).bit_count())
                result[destination,source,row,column]=sign
    return result

def sector_energy(projected,interaction,up,down):
    density_up,matrix_up = projected[up]
    density_down,matrix_down = projected[down]
    dimension_up = density_up.shape[1]
    dimension_down = density_down.shape[1]
    matrix = (density_up.reshape(len(interaction),-1).T @ (interaction[:,None]*density_down.reshape(len(interaction),-1))).reshape(dimension_up,dimension_up,dimension_down,dimension_down).transpose(0,2,1,3).reshape(dimension_up*dimension_down,-1)
    matrix += np.kron(matrix_up,np.eye(dimension_down))+np.kron(np.eye(dimension_up),matrix_down)
    return lowest(matrix,1,2e-6)[0][0]

def calculate(hopping,interaction,potential,counts=(4,6)):
    sites = len(interaction)
    half = sites//2
    bare = -hopping+np.diag(potential)
    density = np.ones(sites)*0.5
    for iteration in range(70):
        energies,orbitals = np.linalg.eigh(bare+np.diag(interaction*density))
        new_density = np.sum(orbitals[:,:half]**2,axis=1)
        if np.max(np.abs(density-new_density))<1e-8:
            break
        density = 0.7*density+0.3*new_density
    result = [energies[half]-energies[half-1],np.std(density),np.sum(interaction*density**2)]
    for count in counts:
        frozen = half-count//2
        active = orbitals[:,frozen:frozen+count]
        core_density = np.sum(orbitals[:,:frozen]**2,axis=1)
        one_body = active.T@(bare+np.diag(interaction*core_density))@active
        site_density = active[:,:,None]*active[:,None,:]
        projected = {}
        for particles in (count//2-1,count//2,count//2+1):
            basis = operators(count,particles)
            projected[particles] = (np.tensordot(site_density,basis,axes=([1,2],[0,1])),np.tensordot(one_body,basis,axes=([0,1],[0,1])))
        neutral = sector_energy(projected,interaction,count//2,count//2)
        spin = sector_energy(projected,interaction,count//2+1,count//2-1)
        removed = sector_energy(projected,interaction,count//2,count//2-1)
        added = sector_energy(projected,interaction,count//2+1,count//2)
        result.extend([added+removed-2*neutral,spin-neutral,neutral,added-neutral,neutral-removed])
    return result

def features(inputs):
    return np.asarray([calculate(inputs['hopping'][index,:sites,:sites],inputs['interaction'][index,:sites],inputs['potential'][index,:sites]) for index,sites in enumerate(inputs['n_sites'])])

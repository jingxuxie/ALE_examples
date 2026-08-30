import numpy as np

def calculate(hopping,interaction,potential):
    sites=len(interaction)
    half=sites//2
    bare=-hopping+np.diag(potential)
    _,modes=np.linalg.eigh(hopping)
    pattern=np.sign(modes[:,0])
    sectors=np.array([(half,half),(half+1,half-1),(half+1,half),(half,half-1)])
    occupied=(np.arange(sites)[None,None,:]<sectors[:,:,None])
    density=np.empty((4,2,sites))
    density[:,0,:]=sectors[:,0,None]/sites+0.35*pattern
    density[:,1,:]=sectors[:,1,None]/sites-0.35*pattern
    diagonal=np.arange(sites)
    for iteration in range(140):
        matrices=np.broadcast_to(bare,(4,2,sites,sites)).copy()
        matrices[:,:,diagonal,diagonal]+=interaction*density[:,::-1,:]
        values,vectors=np.linalg.eigh(matrices)
        new_density=np.sum(vectors**2*occupied[:,:,None,:],axis=-1)
        change=np.max(np.abs(new_density-density))
        density=0.65*density+0.35*new_density
        if change<2e-7:
            break
    energies=np.sum(values*occupied,axis=(1,2))-np.sum(interaction*density[:,0,:]*density[:,1,:],axis=1)
    result=[energies[2]+energies[3]-2*energies[0],energies[1]-energies[0],energies[0],energies[2]-energies[0],energies[0]-energies[3]]
    magnetization=density[:,0,:]-density[:,1,:]
    total=density[:,0,:]+density[:,1,:]
    result.extend(np.mean(magnetization**2,axis=1))
    result.extend(np.std(total,axis=1))
    result.extend([np.mean(interaction),np.std(interaction),np.std(potential),np.mean((potential+(interaction-interaction.mean())*0.5)**2)])
    return result

def features(inputs):
    return np.asarray([calculate(inputs['hopping'][index,:sites,:sites],inputs['interaction'][index,:sites],inputs['potential'][index,:sites]) for index,sites in enumerate(inputs['n_sites'])])

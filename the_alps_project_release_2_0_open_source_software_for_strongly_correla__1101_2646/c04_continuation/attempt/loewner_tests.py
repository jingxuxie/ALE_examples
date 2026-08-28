from research import *


def realization(case, cutoff=1e-13, count=28):
    dimension = len(case['bare'])
    sample = np.unique(np.r_[np.arange(min(8,len(case['iw']))), np.round(np.geomspace(8,len(case['iw']),count-8)-1).astype(int)])
    nodes = 1j*case['iw'][sample]
    values = case['data'][sample]
    difference = nodes[:,None]-nodes.conj()[None,:]
    adjoint = values.conj().swapaxes(-1,-2)
    overlap = -(values[:,None]-adjoint[None,:])/difference[:,:,None,None]
    hamiltonian = -(nodes[:,None,None,None]*values[:,None]-nodes.conj()[None,:,None,None]*adjoint[None,:])/difference[:,:,None,None]
    overlap = overlap.transpose(0,2,1,3).reshape(len(nodes)*dimension,-1)
    hamiltonian = hamiltonian.transpose(0,2,1,3).reshape(len(nodes)*dimension,-1)
    coupling = values.reshape(-1,dimension)
    hcoupling = (nodes[:,None,None]*values-np.eye(dimension)).reshape(-1,dimension)
    overlap = np.block([[np.eye(dimension),coupling.conj().T],[coupling,overlap]])
    hamiltonian = np.block([[case['moments'][1],hcoupling.conj().T],[hcoupling,hamiltonian]])
    coupling = np.r_[np.eye(dimension),coupling]
    normalization = 1/np.sqrt(np.diag(overlap).real)
    overlap = hermitian(normalization[:,None]*overlap*normalization[None,:])
    hamiltonian = hermitian(normalization[:,None]*hamiltonian*normalization[None,:])
    coupling = normalization[:,None]*coupling
    eigenvalues,vectors = la.eigh(overlap)
    selected = eigenvalues > eigenvalues[-1]*cutoff
    inverse_root = (vectors[:,selected]/np.sqrt(eigenvalues[selected])).conj().T
    reduced = hermitian(inverse_root@hamiltonian@inverse_root.conj().T)
    energies,rotation = la.eigh(reduced)
    projected = rotation.conj().T@inverse_root@coupling
    residues = np.einsum('ki,kj->kij',projected.conj(),projected)
    return energies,residues,eigenvalues


def run():
    for kind in ['finite','scalarband','band','band2']:
        for noise in [0,2e-13]:
            case = generated(kind,error=noise)
            print('\n',kind,noise,flush=True)
            for cutoff in [1e-10,1e-11,1e-12,1e-13,1e-14,1e-15,1e-16]:
                energies,residues,eigenvalues = realization(case,cutoff)
                prediction = green_from_spectrum(case['omega']+1j*case['eta'],energies,residues)
                fitted = green_from_spectrum(1j*case['iw'],energies,residues)
                print(cutoff,len(energies),'fit',np.max(np.abs(fitted-case['data'])),'metrics',metrics(prediction,case),flush=True)


if __name__=='__main__':
    run()

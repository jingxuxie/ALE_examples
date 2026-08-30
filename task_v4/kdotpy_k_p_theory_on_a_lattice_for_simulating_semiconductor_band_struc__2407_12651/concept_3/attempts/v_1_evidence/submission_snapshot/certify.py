import sys
import json
import numpy as np
from search import ASSETS, pack, unpack, manufacturing_tail, features

PAULI = np.array([[[1,0],[0,1]],[[0,1],[1,0]],[[0,-1j],[1j,0]],[[1,0],[0,-1]]],complex)
axis = np.arange(8)*2*np.pi/8
horizontal, vertical = np.meshgrid(axis,axis,indexing='ij')
offset, basis = features(horizontal,vertical)
H_OFFSET = np.fft.fft2(np.einsum('xyd,dab->xyab',offset,PAULI),axes=(0,1))/64
H_BASIS = np.fft.fft2(np.einsum('xydj,dab->xyjab',basis,PAULI),axes=(0,1))/64
frequencies = np.fft.fftfreq(8)*8
RX, RY = np.meshgrid(frequencies,frequencies,indexing='ij')

def constants(params, gap=3.1):
    hopping = H_OFFSET + np.einsum('xyjab,j->xyab',H_BASIS,params)
    norms = np.linalg.svd(hopping,compute_uv=False)[...,0]
    norms = norms*(1+1e-12)+1e-14
    lx = np.sum(abs(RX)*norms)
    ly = np.sum(abs(RY)*norms)
    qx = np.sum(RX**2*norms)+.06
    qy = np.sum(RY**2*norms)+.06
    linear = np.array([lx+.06,ly+.06,1,np.sqrt(2)])
    quadratic = np.array([qx,qy,0,0])
    spacing = np.array([2*np.pi/320,2*np.pi/320,.025,.03])
    pad = 2e-10*(1+np.sum(norms))
    preliminary = gap - np.dot(linear,spacing)-2*pad
    epsilon = np.sum((quadratic+2*linear**2/preliminary)*spacing**2/8)
    eta = manufacturing_tail(unpack(params))
    return {'Lx':lx,'Ly':ly,'Qx':qx,'Qy':qy,'g_star':preliminary,'epsilon':epsilon,'eta':eta,'padding':pad,'correction':2*(epsilon+eta+pad)}

def certificate(params, mesh=320, topology=True):
    axis = np.linspace(-np.pi,np.pi,mesh,endpoint=False)
    horizontal, vertical = np.meshgrid(axis,axis,indexing='ij')
    offset, basis = features(horizontal,vertical)
    nominal = offset+np.einsum('...dj,j->...d',basis,params)
    width = 0.
    direct = np.inf
    indirect = np.inf
    for mass_error in np.linspace(-.05,.05,5):
        for anisotropy in np.linspace(-.06,.06,5):
            values = nominal.copy()
            values[...,3] += mass_error
            values[...,1] += anisotropy*np.sin(horizontal)
            values[...,2] -= anisotropy*np.sin(vertical)
            matrix = np.einsum('...d,dab->...ab',values,PAULI)
            energies = np.linalg.eigvalsh(matrix)
            lower, upper = energies[...,0],energies[...,1]
            width=max(width,float(np.ptp(lower)))
            direct=min(direct,float(np.min(upper-lower)))
            indirect=min(indirect,float(upper.min()-lower.max()))
    report = constants(params,direct)
    report.update({'sampled_bandwidth':width,'sampled_direct_gap':direct,'sampled_indirect_gap':indirect,'W_cert':width+report['correction'],'direct_cert':direct-report['correction'],'indirect_cert':indirect-report['correction'],'channels':int(np.count_nonzero(params[1:]))})
    report['score']=min(1,.175/report['W_cert'],report['direct_cert']/3,report['indirect_cert']/3)
    if topology:
        report['topology']=[topology_check(params,shift) for shift in [0,.371]]
    return report

def topology_check(params,shift=0):
    mesh=128
    axis=-np.pi+(np.arange(mesh)+shift)*2*np.pi/mesh
    horizontal,vertical=np.meshgrid(axis,axis,indexing='ij')
    offset,basis=features(horizontal,vertical)
    values=offset+np.einsum('...dj,j->...d',basis,params)
    matrix=np.einsum('...d,dab->...ab',values,PAULI)
    eigenvalues,eigenvectors=np.linalg.eigh(matrix)
    vectors=eigenvectors[...,0]
    phases=np.random.default_rng(1928).uniform(-np.pi,np.pi,(mesh,mesh))
    vectors=vectors*np.exp(1j*phases)[...,None]
    links_x=np.sum(vectors.conj()*np.roll(vectors,-1,axis=0),axis=-1)
    links_y=np.sum(vectors.conj()*np.roll(vectors,-1,axis=1),axis=-1)
    minlink=float(min(abs(links_x).min(),abs(links_y).min()))
    links_x/=abs(links_x)
    links_y/=abs(links_y)
    phases=np.angle(links_x*np.roll(links_y,-1,axis=0)*np.roll(links_x,-1,axis=1).conj()*links_y.conj())
    norms=np.linalg.norm(values[...,1:],axis=-1)
    unit=values[...,1:]/norms[...,None]
    right=np.roll(unit,-1,axis=0)
    up=np.roll(unit,-1,axis=1)
    diagonal=np.roll(right,-1,axis=1)
    def solid(first,second,third):
        numerator=np.einsum('...d,...d->...',first,np.cross(second,third))
        denominator=1+np.sum(first*second,axis=-1)+np.sum(second*third,axis=-1)+np.sum(third*first,axis=-1)
        return 2*np.arctan2(numerator,denominator)
    degree=np.sum(solid(unit,right,diagonal)+solid(unit,diagonal,up))/(4*np.pi)
    bounds=constants(params)
    return {'chern':float(phases.sum()/(2*np.pi)),'degree':float(degree),'max_plaquette_phase':float(abs(phases).max()),'min_link':minlink,'homotopy_radius':float((bounds['Lx']+bounds['Ly'])*2*np.pi/mesh),'min_radius':float(norms.min())}

if __name__=='__main__':
    params=pack(json.load(open(sys.argv[1])))
    print(json.dumps(certificate(params),indent=2))

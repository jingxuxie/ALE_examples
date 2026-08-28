from research import *
from continuation import continue_matrix
from solve import solve
from test_solver import request_from_case


def make_case(kind,dimension,seed,noise=0,eta=.08):
    rng = np.random.default_rng(seed)
    def random_matrix(size):
        return rng.normal(size=(size,size))+1j*rng.normal(size=(size,size))
    if isinstance(kind,int):
        total = kind
        bare = hermitian(random_matrix(dimension))*.3
        bath = np.linspace(-3,3,total-dimension)+rng.uniform(-.03,.03,size=total-dimension)
        coupling = (rng.normal(size=(dimension,len(bath)))+1j*rng.normal(size=(dimension,len(bath))))*.13
        hamiltonian = np.block([[bare,coupling],[coupling.conj().T,np.diag(bath)]])
        energies,vectors = la.eigh(hamiltonian)
        residues = np.einsum('ik,jk->kij',vectors[:dimension],vectors[:dimension].conj())
    else:
        count = 100
        phase = 2*np.pi*np.arange(count)/count
        phase_x,phase_y = np.meshgrid(phase,phase)
        bare = hermitian(random_matrix(dimension))*.4
        coefficients = hermitian(np.array([random_matrix(dimension) for index in range(4)]))*.22
        hamiltonian = bare + np.cos(phase_x.ravel())[:,None,None]*coefficients[0]+np.sin(phase_x.ravel())[:,None,None]*coefficients[1]
        hamiltonian += np.cos(phase_y.ravel())[:,None,None]*coefficients[2]+np.sin(phase_y.ravel())[:,None,None]*coefficients[3]
        energies,vectors = np.linalg.eigh(hamiltonian)
        residues = np.einsum('kia,kja->kaij',vectors,vectors.conj()).reshape(-1,dimension,dimension)/count**2
        energies = energies.ravel()
    moments = [np.einsum('k,kij->ij',energies**order,residues) for order in range(3)]
    iw = np.unique(np.r_[np.pi/(10+seed*7)*(2*np.arange(45)+1),np.geomspace(8,170,40)])
    omega = np.linspace(min(energies)-.4,max(energies)+.4,181)
    data = green_from_spectrum(1j*iw,energies,residues)
    data += noise*.2*(rng.uniform(-1,1,data.shape)+1j*rng.uniform(-1,1,data.shape))
    target = green_from_spectrum(omega+1j*eta,energies,residues)
    return dict(iw=iw,data=data,moments=moments,bare=bare,omega=omega,eta=eta,support=[min(energies)-.2,max(energies)+.2],error=max(noise,2e-13),target=target)


def run():
    cases = [(total,dimension,seed,noise) for total in [8,16,24,32] for dimension,seed,noise in [(2,2,0),(4,4,2e-13)]]
    cases += [('2d',dimension,seed,noise) for dimension,seed,noise in [(2,1,0),(3,2,2e-13),(4,3,0),(2,2,2e-9)]]
    for kind,dimension,seed,noise in cases:
        case = make_case(kind,dimension,seed,noise)
        center = np.mean(case['support']);scale = np.diff(case['support'])[0]/2
        identity = np.eye(dimension)
        moments = [identity,(case['moments'][1]-center*identity)/scale,(case['moments'][2]-2*center*case['moments'][1]+center**2*identity)/scale**2]
        metadata = {}
        started = time.monotonic()
        prediction = continue_matrix((1j*case['iw']-center)/scale,case['data']*scale,moments,(case['omega']+1j*case['eta']-center)/scale,case['error']*scale,metadata=metadata)/scale
        print('STRESS',kind,dimension,seed,noise,metrics(prediction,case),metadata,'seconds',time.monotonic()-started,flush=True)
    for dimension,seed in [(2,1),(3,2)]:
        case = make_case('2d',dimension,seed,0)
        request = request_from_case(case)
        started = time.monotonic()
        prediction = unpack(solve(request)['G_retarded'])
        print('FULL2D',dimension,metrics(prediction,case),'seconds',time.monotonic()-started,flush=True)


if __name__=='__main__':
    run()

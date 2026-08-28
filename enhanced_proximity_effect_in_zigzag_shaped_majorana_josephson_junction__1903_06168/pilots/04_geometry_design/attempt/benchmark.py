from lab import *
from scipy.sparse.linalg import LinearOperator

with open(Path(__file__).resolve().parent.parent / 'participant' / 'input' / 'example.json') as handle:
    request = json.load(handle)
model = ForwardModel(request, geometry_arrays(request, request['baseline_geometry']), nominal_scenario(request))
for clean, order, threshold in [(False,'COLAMD',1), (True,'COLAMD',1),(True,'MMD_AT_PLUS_A',1),(True,'MMD_AT_PLUS_A',0.01),(True,'MMD_AT_PLUS_A',0),(True,'COLAMD',0.01)]:
    matrix=model.hamiltonian(1)
    if clean:
        matrix.eliminate_zeros()
    started=time.monotonic()
    factor=splu(matrix,permc_spec=order,diag_pivot_thresh=threshold)
    factor_time=time.monotonic()-started
    inverse=LinearOperator(matrix.shape,matvec=factor.solve,dtype=complex)
    energies,states=eigsh(matrix,k=4,sigma=0,which='LM',OPinv=inverse,tol=1e-7,v0=np.random.RandomState(17).normal(size=model.dimension))
    print(clean,order,threshold,'nnz',matrix.nnz,'fill',factor.L.nnz+factor.U.nnz,'factor',factor_time,'total',time.monotonic()-started,'E',energies,'err',np.max(np.linalg.norm(matrix@states-states*energies,axis=0)),flush=True)

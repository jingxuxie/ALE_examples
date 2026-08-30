import quiet
import search as engine
from search import np,jax,jnp,json,Path,time,oracle,axes,basis,free,artifact
from scipy.optimize import minimize,NonlinearConstraint,Bounds
from scipy.sparse.linalg import LinearOperator

settings=jnp.array([0.,1.,.097,.0047])

@jax.jit
def outputs(current):
    return quiet.outputs(current,settings).at[37].add(-.003)

jacobian=jax.jit(jax.jacfwd(outputs))
gradient_lagrangian=jax.grad(lambda current,weights:jnp.dot(outputs(current),weights),argnums=0)

@jax.jit
def hessian_product(current,weights,direction):
    return jax.jvp(lambda state:gradient_lagrangian(state,weights),(current,),(direction,))[1]

def hessian(current,weights):
    return LinearOperator((138,138),matvec=lambda direction:np.asarray(hessian_product(current,weights,np.asarray(direction).reshape(-1))))

def main():
    filename='polished.json' if Path('polished.json').exists() else 'quiet_path7.json'
    data=json.loads(Path(filename).read_text())
    initial=np.r_[np.einsum('kij,ij->k',axes,np.array(data['pair_matrix'])),data['amplitudes']]
    print('COMPILE',flush=True)
    values=np.asarray(outputs(initial))
    objective_weights=np.zeros(len(values)); objective_weights[0]=1
    print('HESS',np.linalg.norm(hessian_product(initial,objective_weights,np.ones(138))),flush=True)
    limits=np.array([1.498*(1 if row==column else np.sqrt(2)) for row in range(15) for column in range(row,15)]+[1.248]*18)
    constraint=NonlinearConstraint(lambda current:np.asarray(outputs(current))[1:],
        np.r_[np.zeros(34),np.zeros(len(values)-35)],np.r_[np.zeros(34),np.full(len(values)-35,np.inf)],
        jac=lambda current:np.asarray(jacobian(current))[1:],hess=lambda current,weights:hessian(current,np.r_[0,weights]))
    started=time.time()
    def callback(current,state):
        if state.nit%20==0:
            print('ITER',state.nit,round(time.time()-started,2),'optimal',state.optimality,'violation',state.constr_violation,'barrier',state.barrier_parameter,np.asarray(engine.metrics(current)).round(9).tolist(),flush=True)
            np.savez('trust_live.npz',variables=current)
    result=minimize(lambda current:float(outputs(current)[0]),initial,jac=lambda current:np.asarray(jacobian(current))[0],
        hess=lambda current:hessian(current,objective_weights),method='trust-constr',bounds=Bounds(-limits,limits),constraints=[constraint],callback=callback,
        options={'maxiter':1200,'gtol':1e-9,'xtol':1e-11,'barrier_tol':1e-11,'initial_barrier_parameter':1e-5,'initial_barrier_tolerance':1e-5,'initial_tr_radius':.05,'verbose':0})
    current=result.x
    matrix=np.einsum('k,kij->ij',current[:120],axes)
    stationary=oracle.solve(free+np.einsum('k,kij->ij',current[:120],basis),current[120:])
    Path('trust_result.json').write_text(json.dumps(artifact(matrix,stationary.amplitudes)))
    np.savez('trust_result.npz',variables=np.r_[current[:120],stationary.amplitudes])
    print('RESULT',result.message,np.asarray(engine.metrics(np.r_[current[:120],stationary.amplitudes])).tolist(),flush=True)

if __name__=='__main__':main()

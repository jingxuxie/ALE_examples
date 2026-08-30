import json
import time
from pathlib import Path
import numpy as np
from scipy.linalg import null_space
from scipy.optimize import minimize
from search_model import oracle,axes,hbase,haxes,hfbase,hfaxes,structured,bounds
from api import artifact,screen

data=np.load('small_parent.npz');active=data['active'];exact_active=data['exact_active'];values=data['values'];count=len(active);selection=np.array(structured)
amplitudes=np.zeros(18);amplitudes[active]=values[:count];multipliers=np.zeros(18);multipliers[active]=values[count:2*count]
exact=oracle.ref.copy();exact[exact_active]=values[2*count:];exact/=np.linalg.norm(exact)


def equations(hamiltonian):
    residual,jacobian,transformed,_,_=oracle.equations(hamiltonian,amplitudes)
    exact_residual=hamiltonian@exact-(exact@hamiltonian@exact)*exact
    return np.concatenate((residual[active],(transformed[0,oracle.targets]+jacobian.T@multipliers)[active],exact_residual[exact_active]))


linear=np.array([equations(derivative) for derivative in haxes[selection]]).T;offset=equations(hbase)
origin=np.linalg.lstsq(linear,-offset,rcond=1e-10)[0];null=null_space(linear,rcond=1e-10)
orthogonal=null_space(exact.reshape(1,-1));exact_base=exact@hbase@exact;exact_axes=np.einsum('i,kij,j->k',exact,haxes[selection],exact)
projected_base=orthogonal.T@(hbase-exact_base*np.eye(20))@orthogonal
projected_axes=np.einsum('ai,kab,bj->kij',orthogonal,haxes[selection]-exact_axes[:,None,None]*np.eye(20),orthogonal)
limits=np.array([upper for lower,upper in bounds(selection)])
cut_rows=[*null,*(-null)];cut_bounds=list(-limits-origin)+list(origin-limits)
parameters=np.zeros(null.shape[1]);started=time.monotonic()
print('null',null.shape,'linear residual',np.linalg.norm(linear@origin+offset),flush=True)
for iteration in range(80):
    coefficients=origin+null@parameters
    gap_matrix=projected_base+np.einsum('k,kij->ij',coefficients,projected_axes)
    hessians=hfbase+np.einsum('k,kbij->bij',coefficients,hfaxes[selection])
    minima=[]
    for matrix,base,derivatives,threshold in [(gap_matrix,projected_base,projected_axes,.103), (hessians[0],hfbase[0],hfaxes[selection,0],.053), (hessians[1],hfbase[1],hfaxes[selection,1],.053)]:
        eigenvalues,eigenvectors=np.linalg.eigh(matrix);minima.append(eigenvalues[0])
        for index in np.where(eigenvalues<threshold+1e-7)[0]:
            vector=eigenvectors[:,index];coeff=np.einsum('i,kij,j->k',vector,derivatives,vector)
            cut_rows.append(coeff@null);cut_bounds.append(threshold-vector@base@vector-coeff@origin)
    print(iteration,'minima',minima,'norm',np.linalg.norm(coefficients),'entry',max(abs(coefficients)/limits),flush=True)
    if minima[0]>.103-1e-8 and min(minima[1:])>.053-1e-8 and max(abs(coefficients)/limits)<1+1e-8:
        break
    matrix=np.array(cut_rows);lower=np.array(cut_bounds)
    answer=minimize(lambda point:(np.sum((origin+null@point)**2),2*null.T@(origin+null@point)),parameters,jac=True,method='SLSQP',constraints={'type':'ineq','fun':lambda point:matrix@point-lower,'jac':lambda point:matrix},options={'maxiter':1000,'ftol':1e-11})
    parameters=answer.x
    if min(matrix@parameters-lower)<-1e-5:
        print('infeasible',answer.message,min(matrix@parameters-lower),flush=True)
        break
coefficients=origin+null@parameters;pair_matrix=np.einsum('k,kij->ij',coefficients,axes[selection]);Path('parent_candidate.json').write_text(json.dumps(artifact(pair_matrix,amplitudes),indent=2))
diagnostic,_=screen(pair_matrix,amplitudes,oracle)
print('FINAL',diagnostic,'seconds',time.monotonic()-started,flush=True)

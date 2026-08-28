from research import *
from scipy.optimize import least_squares


def real_residues(nodes, values, roots, moments):
    basis = 1/(nodes[:,None]-roots)
    system = np.r_[basis.real,basis.imag]
    target = np.concatenate([hermitian(values),hermitian(values/1j)]).reshape(len(nodes)*2,-1)
    constraints = np.array([roots**order for order in range(len(moments))])
    constant = np.array(moments).reshape(len(moments),-1)
    particular = la.lstsq(constraints,constant,lapack_driver='gelsy')[0]
    nullspace = la.null_space(constraints)
    residual = target-system@particular
    coefficients = la.lstsq(system@nullspace,residual,lapack_driver='gelsy')[0]
    residues = particular+nullspace@coefficients
    residual = system@residues-target
    return residues.reshape((-1,)+values.shape[1:]),residual


def refine(nodes, values, roots, moments, iterations=30):
    scale = max(np.max(np.abs(roots)),1)
    def fun(energies):
        residues,residual = real_residues(nodes,values,energies*scale,moments)
        return np.r_[residual.real.ravel(),residual.imag.ravel()]*1e6
    solution = least_squares(fun,roots/scale,ftol=1e-12,xtol=1e-12,gtol=1e-10,max_nfev=iterations,diff_step=1e-5)
    roots = solution.x*scale
    residues,residual = real_residues(nodes,values,roots,moments)
    return roots,residues,la.norm(residual)


def run():
    for kind in ['finite','scalarband','band','band2']:
        case = generated(kind)
        nodes = np.r_[1j*case['iw'],-1j*case['iw']]
        values = np.r_[case['data'],case['data'].conj().swapaxes(-1,-2)]
        history = aaa(nodes,values,tolerance=1e-12,maximum=20,paired=True)
        print('\n',kind,flush=True)
        for model in history[-3:]:
            energies = poles(model)
            energies = np.sort(energies.real[(np.abs(energies.imag)<1e-4)&(energies.real>case['support'][0])&(energies.real<case['support'][1])])
            residues,residual = real_residues(1j*case['iw'],case['data'],energies,case['moments'])
            prediction = green_from_spectrum(case['omega']+1j*case['eta'],energies,residues)
            weights = np.linalg.eigvalsh(residues)
            print('before',len(energies),la.norm(residual),metrics(prediction,case),'negative',-weights[weights<0].sum(),'rank1',weights[:,:-1].sum(),flush=True)
            energies,residues,error = refine(1j*case['iw'],case['data'],energies,case['moments'])
            prediction = green_from_spectrum(case['omega']+1j*case['eta'],energies,residues)
            weights = np.linalg.eigvalsh(residues)
            print('after',len(energies),error,metrics(prediction,case),'negative',-weights[weights<0].sum(),'rank1',weights[:,:-1].sum(),flush=True)


if __name__=='__main__':
    run()

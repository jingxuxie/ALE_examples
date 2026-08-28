import numpy as np
from scipy.sparse.linalg import LinearOperator, eigsh
from physics import ForwardModel, ZEEMAN, PAIR_IMAG, PAIR_REAL, feasibility
from fast_physics import reflection_basis, factorize


def derivatives(request, masks, scenario, momenta=(0.0, np.pi), bands=4):
    model = ForwardModel(request, masks, scenario)
    energies_all = []
    slopes_all = []
    fixed = request['fixed_physics']
    phase = fixed['phase_rad']/2
    changes = [
        -scenario['zeeman_mev']*ZEEMAN + fixed['delta_mev']*(np.cos(phase)*PAIR_REAL - np.sin(phase)*PAIR_IMAG),
        -scenario['zeeman_mev']*ZEEMAN + fixed['delta_mev']*(np.cos(phase)*PAIR_REAL + np.sin(phase)*PAIR_IMAG),
    ]
    for momentum in momenta:
        matrix = model.hamiltonian(momentum)
        basis = None
        if abs(momentum) < 1e-10 or abs(momentum-np.pi) < 1e-10:
            basis = reflection_basis(model.nx, model.ny, abs(momentum-np.pi) < 1e-10)
            matrix = (basis.T @ matrix @ basis).tocsc()
        matrix.eliminate_zeros()
        factor = factorize(matrix)
        inverse = LinearOperator(matrix.shape, matvec=factor.solve, dtype=complex)
        energies, vectors = eigsh(matrix, k=bands, sigma=0.0, which='LM', OPinv=inverse,
                                 tol=2e-7, ncv=max(20,2*bands+2), maxiter=300,
                                 v0=np.random.RandomState(17).normal(size=matrix.shape[0]))
        error = np.max(np.linalg.norm(matrix @ vectors-vectors*energies,axis=0))
        if error > 2e-5:
            raise ArithmeticError('Derivative eigensystem residual')
        if basis is not None:
            vectors = basis @ vectors
        states = vectors.reshape(model.nx, model.ny, 4, bands).transpose(3,1,0,2)
        slopes = np.stack([np.einsum('byxc,cd,byxd->byx', states.conj(), change, states).real for change in changes],axis=1)
        slopes *= np.sign(energies)[:,None,None,None]
        energies_all.extend(np.abs(energies))
        slopes_all.extend(slopes)
    return np.asarray(energies_all), np.asarray(slopes_all)


def predicted_merit(energies, groups):
    gaps = np.asarray([np.min(energies[group]) for group in groups])
    return .5*np.mean(gaps)+.5*np.min(gaps)


def boundary_candidates(request, masks, samples, counts=(2,4,8,16,24), noise=0.0, seed=0, singles=0):
    energies = np.concatenate([sample[0] for sample in samples])
    slopes = np.concatenate([sample[1] for sample in samples])
    offsets = np.cumsum([0]+[len(sample[0]) for sample in samples])
    groups = [slice(offsets[index],offsets[index+1]) for index in range(len(samples))]
    nx = request['grid']['nx']
    ny = request['grid']['ny']
    rows = request['manufacturing']['minimum_contact_rows']
    top = np.argmax(masks['sc_top'],axis=0)
    bottom = ny-1-np.argmax(masks['sc_bottom'][::-1],axis=0)
    moves = []
    generator = np.random.RandomState(seed)
    for column in range(nx//2+1):
        columns = sorted(set([column,(-column)%nx]))
        for contact, heights in enumerate((top,bottom)):
            for direction in (-1,1):
                height = int(heights[column])
                if contact == 0:
                    row = height if direction == 1 else height-1
                    material = -direction
                else:
                    row = height+1 if direction == 1 else height
                    material = direction
                if not rows <= row < ny-rows:
                    continue
                change = material*np.sum(slopes[:,contact,row,columns],axis=1)
                moves.append((contact,columns,row,material>0,change,generator.normal()*noise))
    working = {name:mask.copy() for name,mask in masks.items()}
    names = ('sc_top','sc_bottom')
    results = []
    ranking = sorted(range(len(moves)),key=lambda index: predicted_merit(energies+moves[index][4],groups),reverse=True)
    for index in ranking:
        if len(results) >= singles:
            break
        contact, columns, row, value, change, perturbation = moves[index]
        previous = working[names[contact]][row,columns].copy()
        working[names[contact]][row,columns] = value
        if feasibility(request,working)['valid']:
            results.append({name:mask.copy() for name,mask in working.items()})
        working[names[contact]][row,columns] = previous
    occupied = set()
    for number in range(1,max(counts)+1):
        ranking = sorted(range(len(moves)),key=lambda index: predicted_merit(energies+moves[index][4],groups)+moves[index][5],reverse=True)
        selected = None
        for index in ranking:
            contact, columns, row, value, change, perturbation = moves[index]
            if (contact,columns[0]) in occupied:
                continue
            previous = working[names[contact]][row,columns].copy()
            working[names[contact]][row,columns] = value
            valid = feasibility(request,working)['valid']
            if valid:
                selected = index
                break
            working[names[contact]][row,columns] = previous
        if selected is None:
            break
        occupied.add((contact,columns[0]))
        energies += change
        if number in counts:
            results.append({name:mask.copy() for name,mask in working.items()})
    return results

from patterns import *
from scipy import sparse


def optimize_direction(data, masks, coefficients=None, samples=512, signs_options=None):
    proposals = proposal(data, masks)
    if not proposals:
        return []
    rough, initial, null, errors = proposals[0]
    stride = max(1, len(data[4]) // samples)
    grid = data[4][::stride] @ null
    density = data[5][::stride]
    density = (density / density.sum(axis=0)).mean(axis=1)
    sample_count, dimension = grid.shape
    projected = errors @ null
    projected /= max(np.linalg.norm(projected, axis=1))
    inequalities = sparse.vstack([
        sparse.hstack([sparse.csr_matrix(grid), -sparse.eye(sample_count)]),
        sparse.hstack([sparse.csr_matrix(-grid), -sparse.eye(sample_count)]),
    ], format='csr')
    rhs = np.zeros(2 * sample_count)
    objective = np.concatenate([np.zeros(dimension), density])
    bounds = [(None, None)] * dimension + [(0, None)] * sample_count
    candidates = []
    for signs in (signs_options if signs_options is not None else ([1, 1, 1], [1, 1, -1], [1, -1, 1], [1, -1, -1])):
        signed = np.array(signs)[:, None] * projected
        matrix = sparse.vstack([inequalities, sparse.hstack([-signed, sparse.csr_matrix((3, sample_count))])], format='csr')
        result = linprog(objective, A_ub=matrix, b_ub=np.concatenate([rhs, -np.ones(3)]), bounds=bounds, method='highs', options={'dual_feasibility_tolerance': 1e-9, 'primal_feasibility_tolerance': 1e-9})
        if result.success:
            coefficients = null @ result.x[:dimension]
            coefficients /= abs(coefficients).sum()
            l1 = abs(data[4] @ coefficients) @ data[5]
            predicted = abs(errors @ coefficients) * data[5].sum(axis=0)
            ratios = predicted / (1e-5 * l1)
            candidates.append((ratios.min(), coefficients, ratios))
    return sorted(candidates, key=lambda entry: entry[0], reverse=True)


def main():
    finalists = np.load('finalists.npy', allow_pickle=True)
    best = 0
    seen = set()
    for rank, (oldmargin, witness, masks, initial) in enumerate(finalists):
        tag = (witness['bin'], masks)
        if tag in seen:
            continue
        seen.add(tag)
        data = precompute(witness)
        candidates = optimize_direction(data, masks, samples=1024)
        if not candidates:
            continue
        margin, coefficients, ratios = candidates[0]
        print('OPT',rank,witness['bin'],masks,oldmargin,margin,ratios,flush=True)
        candidate = integer_witness(witness,coefficients)
        report = measure(candidate,trace=True,kernel=kernel)
        screen = report['worst_screen_margin']
        print('SCREEN',screen,[(entry['target']['panels'],entry['screen_error'],entry['screen_l1']) for entry in report['families'].values()],flush=True)
        if screen > best:
            best = screen
            Path('optimized_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('optimized_report.json').write_text(json.dumps(report,indent=2)+'\n')
            np.save('optimized_best.npy',np.array([witness,masks,coefficients],dtype=object),allow_pickle=True)


if __name__ == '__main__':
    main()

from design import *
import itertools
import time


def precompute(witness):
    embedded, guard, discrepancy, actual = [], [], [], []
    for index in range(8):
        constraints, error = matrices(witness, index)
        embedded.append(constraints[:3])
        guard.append(constraints[3:6])
        discrepancy.append(constraints[6:])
        actual.append(error)
    points = (np.arange(1024) + .5) / 1024
    lower, upper = BINS[witness['bin']]
    scale = 2 * (upper - lower) * COLOR * kernel(lower + (upper - lower) * points)
    scale *= response(points, witness)[:, None] / len(points)
    return np.array(embedded), np.array(guard), np.array(discrepancy), np.array(actual), basis(points, witness), abs(scale)


def proposal(data, masks):
    embedded, guard, discrepancy, actual, grid, scale = data
    rows = []
    errors = []
    for family, indices in enumerate(masks):
        for index in indices:
            rows.extend([embedded[index, family], guard[index, family]])
        for parent in sorted(set(index // 2 for index in indices)):
            rows.append(discrepancy[2 * parent, family])
        errors.append(actual[list(indices), family].sum(axis=0))
    rows = np.array(rows)
    rows /= np.linalg.norm(rows, axis=1)[:, None]
    null = null_space(rows, rcond=1e-13)
    if null.shape[1] == 0:
        return []
    errors = np.array(errors) / scale.sum(axis=0)[:, None]
    projected = errors @ null
    directions = np.array([[1, 1, 1], [1, 1, -1], [1, -1, 1], [1, -1, -1]]) @ projected
    directions = directions @ null.T
    norms = np.linalg.norm(directions, axis=1)
    directions /= np.maximum(norms[:, None], 1e-100)
    predicted = directions @ errors.T
    rough = np.min(abs(predicted), axis=1)
    best_index = rough.argmax()
    coefficients = directions[best_index]
    return [(rough[best_index], coefficients, null, errors)]


def search():
    rng = np.random.default_rng(321)
    best = 0
    finalists = []
    started = time.monotonic()
    for name in BINS:
        witness = dict(version=1, bin=name, band_start=53, tilt=-1, curvature=-4)
        data = precompute(witness)
        patterns = []
        for indices in itertools.product(range(4), repeat=3):
            patterns.append(tuple((2 * index, 2 * index + 1) for index in indices))
        for indices in itertools.product(range(8), repeat=3):
            patterns.append(tuple((index,) for index in indices))
        for trial in range(12000):
            lengths = rng.choice([1, 2, 3, 4], size=3, p=[.10, .45, .35, .10])
            masks = tuple(tuple(sorted(rng.choice(8, length, replace=False))) for length in lengths)
            count = sum(2 * len(mask) + len(set(index // 2 for index in mask)) for mask in masks)
            if count < 24:
                patterns.append(masks)
        for number, masks in enumerate(patterns):
            proposals = proposal(data, masks)
            for rough, coefficients, null, errors in proposals:
                if rough > best * 2e-6 or len(finalists) < 30:
                    l1 = abs(data[4] @ coefficients) @ data[5]
                    predicted = abs(errors @ coefficients) * data[5].sum(axis=0)
                    ratios = predicted / (1e-5 * l1)
                    margin = ratios.min()
                    if margin > best:
                        best = margin
                        print('BEST',name,number,masks,'ratio',ratios,'rough',rough,'seconds',time.monotonic()-started,flush=True)
                    finalists.append((margin, witness.copy(), masks, coefficients))
                    finalists.sort(key=lambda entry: entry[0],reverse=True)
                    finalists=finalists[:30]
        print('BIN',name,'best',best,'seconds',time.monotonic()-started,flush=True)
    np.save('finalists.npy',np.array(finalists,dtype=object),allow_pickle=True)
    best_screen = 0
    for rank, (margin,witness,masks,coefficients) in enumerate(finalists):
        try:
            candidate = integer_witness(witness,coefficients)
        except ValueError:
            continue
        report = measure(candidate,trace=True,kernel=kernel)
        result=report['worst_screen_margin']
        print('SCREEN',rank,margin,witness,masks,result,[(entry['target']['panels'],entry['screen_error'],entry['screen_l1']) for entry in report['families'].values()],flush=True)
        if result>best_screen:
            best_screen=result
            Path('pattern_witness.json').write_text(json.dumps(candidate,indent=2)+'\n')
            Path('pattern_report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    search()

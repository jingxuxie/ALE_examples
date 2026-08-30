from investigate import *
from collections import Counter
import argparse
import itertools

def dense_candidate(random):
    point = random.uniform(.0501, .9499)
    center = 2*point-1
    order = int(random.choice([6, 8, 10, 12]))
    first = random.normal(size=order+1)
    first /= np.linalg.norm(first)
    first *= random.uniform(.12, .32)
    first[0] -= cheb.chebval(center, first)
    second = random.normal(size=order+1)
    second /= np.linalg.norm(second)
    second *= random.uniform(.05, .2)
    second[0] -= cheb.chebval(center, second)
    height = 10**random.uniform(-1.87, -1.35)
    third = random.normal(size=order+1)
    third /= np.linalg.norm(third)
    third *= random.uniform(.005, .15)
    third[0] += height-cheb.chebval(center, third)
    depth = 1.03e-7
    positive = depth * 10**random.uniform(.0, 2)
    plateau = depth * random.uniform(1.01, 8)
    vectors = [first, second, third]
    spectral = np.zeros((2*order+1, 4, 4))
    for row in range(3):
        for column in range(row, 3):
            polynomial = cheb.chebmul(vectors[row], vectors[column])
            spectral[:len(polynomial), row, column] = polynomial
            spectral[:, column, row] = spectral[:, row, column]
    envelope_scale = 10**random.uniform(-5, -1)
    envelope = cheb.chebmul([-center, 1], [-center, 1]) * envelope_scale
    spectral[:3, 0, 0] += envelope
    spectral[0, 0, 0] -= depth
    spectral[0, 1, 1] += plateau
    spectral[0, 2, 2] += positive
    document = package(spectral, point)
    return document, dict(point=point, order=order, height=height, positive=positive, plateau=plateau, envelope_scale=envelope_scale)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=3359)
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    stages = Counter()
    best = -1e99
    start = time.time()
    meshes = np.unique(np.concatenate([guard._mesh(profile) for profile in guard.PROFILES]))
    for trial in range(arguments.trials):
        document, parameters = dense_candidate(random)
        coefficients = unpack(document)
        matrix = guard.evaluate_matrices(coefficients, [parameters['point']])[0]
        if min(np.diag(matrix)) < .02 or min(np.linalg.det(matrix[np.ix_(pair,pair)]) for pair in itertools.combinations(range(4),2)) < 1e-5 or max(np.sum(np.abs(coefficients),axis=(0,2))) > 4 or np.max(np.abs(coefficients)) > 1:
            stages['invalid'] += 1
            continue
        meshmin = np.linalg.eigvalsh(guard.evaluate_matrices(coefficients, meshes))[:,0].min()
        if meshmin < -guard.NEGATIVE_TOLERANCE:
            stages['mesh'] += 1
            continue
        candidates = guard.determinant_candidates(coefficients)
        minimum = np.linalg.eigvalsh(guard.evaluate_matrices(coefficients, candidates))[:,0].min()
        stages['determinants'] += 1
        if minimum > best:
            best = minimum
            Path('dense_best.json').write_text(json.dumps(document))
            print('BEST', trial, minimum, parameters, flush=True)
        if minimum >= -guard.NEGATIVE_TOLERANCE:
            reports = guard.screen_all(coefficients)
            count = sum(report['accepted'] for report in reports)
            print('ESCAPE', trial, parameters, reports, flush=True)
            Path(f'dense_escape_{trial}.json').write_text(json.dumps(document))
            if count == 3:
                Path('witness.json').write_text(json.dumps(document))
                break
        if trial % 100 == 0:
            print('PROGRESS', trial, dict(stages), time.time()-start, flush=True)
    print('DONE', dict(stages), time.time()-start, flush=True)

if __name__ == '__main__':
    main()

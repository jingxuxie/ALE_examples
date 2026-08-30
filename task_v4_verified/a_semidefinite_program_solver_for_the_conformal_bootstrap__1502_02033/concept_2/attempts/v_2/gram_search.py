from investigate import *
import argparse
from collections import Counter

def gram_candidate(random, mode=0):
    point = random.uniform(.0501, .9499)
    center = 2*point-1
    order = int(random.choice([5, 7, 9, 11, 12]))
    leading = random.uniform(.15, .45)
    first = np.zeros(order+1)
    first[-1] = leading
    first[0] = -cheb.chebval(center, first)
    height = 10**random.uniform(-2.2, -1.4)
    depth = 1.05e-7
    positive = depth * 10**random.uniform(.2, 2)
    plateau = depth * random.uniform(1.01, 3)
    spectral = np.zeros((2*order+1, 4, 4))
    spectral[:len(cheb.chebmul(first, first)), 0, 0] = cheb.chebmul(first, first)
    spectral[:len(first), 0, 1] = height*first
    spectral[:len(first), 1, 0] = height*first
    spectral[0, 1, 1] = height**2+positive
    spectral[0, 2, 2] = plateau
    envelope = cheb.chebmul([-center, 1], [-center, 1]) * 10**random.uniform(-4, -.5)
    spectral[:3, 0, 0] += envelope
    spectral[0, 0, 0] -= depth
    if mode:
        spectral[:3, 2, 2] += cheb.chebmul([-random.uniform(-.8,.8),1], [-random.uniform(-.8,.8),1])*depth
    spectral = spectral[:, [0, 2, 1, 3]][:, :, [0, 2, 1, 3]]
    document = package(spectral, point)
    return document, dict(point=point, order=order, leading=leading, height=height, depth=depth, positive=positive, plateau=plateau, envelope=envelope.tolist())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=777)
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    stages = Counter()
    best = -1e99
    start = time.time()
    for trial in range(arguments.trials):
        document, parameters = gram_candidate(random)
        coefficients = unpack(document)
        matrix = guard.evaluate_matrices(coefficients, [parameters['point']])[0]
        if min(np.diag(matrix)) < .02 or min(np.linalg.det(matrix[np.ix_(pair,pair)]) for pair in __import__('itertools').combinations(range(4),2)) < 1e-5:
            stages['invalid_principal'] += 1
            continue
        reports = guard.screen_all(coefficients)
        count = sum(report['accepted'] for report in reports)
        rank = count + 1e5*min(report.get('minimum_seen', -1) for report in reports)
        for report in reports:
            stages[report.get('last_stage','failure')] += 1
        if rank > best:
            best = rank
            Path('gram_best.json').write_text(json.dumps(document))
            print('BEST', trial, parameters, reports, flush=True)
        if count == 3:
            break
        if trial % 100 == 0:
            print('PROGRESS', trial, dict(stages), time.time()-start, flush=True)
    print('DONE', dict(stages), time.time()-start, flush=True)

if __name__ == '__main__':
    main()

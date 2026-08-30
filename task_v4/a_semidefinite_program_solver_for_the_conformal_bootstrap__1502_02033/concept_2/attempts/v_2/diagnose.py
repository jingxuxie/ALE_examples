from investigate import *
import itertools
import argparse

def candidates_by_minor(coefficients):
    for size in range(1,5):
        for subset in itertools.combinations(range(4), size):
            determinant = np.zeros(size*(len(coefficients)-1)+1)
            for permutation in itertools.permutations(range(size)):
                inversions = sum(permutation[left]>permutation[right] for left in range(size) for right in range(left+1,size))
                polynomial = np.array([1.0])
                for row,column in enumerate(permutation):
                    polynomial = cheb.chebmul(polynomial, coefficients[:,subset[row],subset[column]])
                determinant[:len(polynomial)] += (-1 if inversions % 2 else 1)*polynomial
            yield subset, determinant

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('witness')
    arguments = parser.parse_args()
    document = json.loads(Path(arguments.witness).read_text())
    coefficients = unpack(document)
    point = float(Fraction(document['x']))
    matrix = guard.evaluate_matrices(coefficients,[point])[0]
    print('point',point,'eigs', np.linalg.eigvalsh(matrix))
    for subset, polynomial in candidates_by_minor(coefficients):
        for stage, original in [('roots',polynomial),('stationary',cheb.chebder(polynomial))]:
            candidates = guard._root_projections(original)
            if len(candidates):
                eigenvalues = np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,candidates))[:,0]
                nearest = candidates[np.argmin(abs(candidates-point))]
                print(subset, stage, 'near',nearest,'distance',nearest-point,'min',eigenvalues.min(),'pval',cheb.chebval(2*point-1,polynomial),'exact',np.linalg.det(matrix[np.ix_(subset,subset)]), 'coeffmax',abs(polynomial).max())
    print(json.dumps(guard.screen_all(coefficients)))

if __name__ == '__main__':
    main()

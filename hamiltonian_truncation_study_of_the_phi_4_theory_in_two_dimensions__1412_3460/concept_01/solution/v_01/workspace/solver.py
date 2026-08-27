from core import solve as compute


def solve(case, archive, cutoff, method='production'):
    mapping = {'production': 'improved', 'raw': 'raw', 'local': 'local'}
    result = compute(case, archive, cutoff, mapping[method])
    result['method'] = method
    return result

def physical_couplings(case):
    coefficients = {}
    for term in case['couplings']:
        key = (term['degree'], term.get('transfer', 0))
        coefficients[key] = coefficients.get(key, 0.0) + term['value']
    return coefficients, 0.0

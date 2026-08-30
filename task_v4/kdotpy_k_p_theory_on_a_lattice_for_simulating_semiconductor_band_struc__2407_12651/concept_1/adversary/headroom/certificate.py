from fractions import Fraction

import numpy as np


def exact_box_dual(formulation, equality_dual, inequality_dual):
    cache = {}

    def dyadic(value):
        value = float(value)
        if value not in cache:
            numerator, denominator = value.as_integer_ratio()
            cache[value] = (numerator, denominator.bit_length() - 1)
        return cache[value]

    equality_dual = np.asarray(equality_dual)
    inequality_dual = np.minimum(np.asarray(inequality_dual), 0.0)
    objective = [dyadic(value) for value in formulation['objective']]
    upper = [dyadic(value) for value in formulation['upper']]
    contributions, constant = [], []
    common_power = max(exponent for numerator, exponent in objective)
    for matrix, right_hand, dual in [(formulation['equalities'], formulation['equality_rhs'], equality_dual),
                                    (formulation['inequalities'], formulation['inequality_rhs'], inequality_dual)]:
        dual_ratios = [dyadic(value) for value in dual]
        entries = matrix.tocoo()
        for row, column, value in zip(entries.row, entries.col, entries.data):
            first, first_power = dyadic(value)
            second, second_power = dual_ratios[row]
            exponent = first_power + second_power
            contributions.append((int(column), first * second, exponent))
            common_power = max(common_power, exponent)
        for value, (dual_numerator, dual_power) in zip(right_hand, dual_ratios):
            numerator, exponent = dyadic(value)
            constant.append((numerator * dual_numerator, exponent + dual_power))
            common_power = max(common_power, exponent + dual_power)
    residual = [numerator << (common_power - exponent) for numerator, exponent in objective]
    for column, numerator, exponent in contributions:
        residual[column] -= numerator << (common_power - exponent)
    final_power = common_power + max(exponent for numerator, exponent in upper)
    total = sum(numerator << (final_power - exponent) for numerator, exponent in constant)
    for reduced, (numerator, exponent) in zip(residual, upper):
        if reduced < 0 and numerator:
            total += (reduced * numerator) << (final_power - common_power - exponent)
    exact = Fraction(total, 1 << final_power)
    downward = float(np.nextafter(float(exact), -np.inf))
    return {'exact_lp_bound_numerator': str(exact.numerator), 'exact_lp_bound_denominator': str(exact.denominator),
            'exact_lp_bound_float_downward': downward, 'lower_bound': downward - 1e-9,
            'scorer_roundoff_guard': 1e-9, 'arithmetic': 'exact dyadic integer accumulation; sign-clipped inequality dual and box residual correction',
            'nonzero_dual_coefficients': int(np.count_nonzero(equality_dual) + np.count_nonzero(inequality_dual))}


def save_certificate(destination, formulation, equality_dual, inequality_dual):
    arrays = {'objective': formulation['objective'], 'upper': formulation['upper'],
              'equality_rhs': formulation['equality_rhs'], 'inequality_rhs': formulation['inequality_rhs'],
              'equality_dual': equality_dual, 'inequality_dual': inequality_dual}
    for name in ['equalities', 'inequalities']:
        matrix = formulation[name].tocoo()
        arrays[name + '_row'] = matrix.row
        arrays[name + '_column'] = matrix.col
        arrays[name + '_data'] = matrix.data
        arrays[name + '_shape'] = matrix.shape
    np.savez_compressed(destination, **arrays)

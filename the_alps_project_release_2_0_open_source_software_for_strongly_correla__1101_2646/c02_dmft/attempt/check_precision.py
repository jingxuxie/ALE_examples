"""Check the Legendre frequency kernel against 120-digit arithmetic."""

from decimal import Decimal, localcontext
import json
from pathlib import Path

import numpy as np
from scipy.special import spherical_jn

import solve
from test_solve import decode, make_legendre


def arctangent_inverse(denominator):
    argument = Decimal(1) / denominator
    power = argument
    result = argument
    order = 1
    while True:
        power *= -argument * argument
        term = power / (2 * order + 1)
        updated = result + term
        if updated == result:
            return updated
        result = updated
        order += 1


def decimal_kernel(count, degree):
    kernel = np.zeros((count, degree), dtype=np.clongdouble)
    phases = [1j, -1, -1j, 1]
    with localcontext() as context:
        context.prec = 120
        pi = 16 * arctangent_inverse(Decimal(5)) - 4 * arctangent_inverse(Decimal(239))
        for index in range(count):
            argument = (Decimal(index) + Decimal("0.5")) * pi
            previous = 1 / argument
            current = previous / argument
            values = [previous, current]
            for order in range(1, degree - 1):
                following = (2 * order + 1) * current / argument - previous
                values.append(following)
                previous, current = current, following
            for order in range(degree):
                value = values[order] * Decimal(2 * order + 1).sqrt()
                kernel[index, order] = np.longdouble(str(value)) * phases[order % 4]
    return kernel


def main():
    exact = decimal_kernel(40, 32)
    orders = np.arange(32)
    arguments = (np.arange(40) + 0.5) * np.pi
    library = spherical_jn(orders[None, :], arguments[:, None])
    library = library * np.where(np.arange(40) % 2 == 0, 1, -1)[:, None]
    library = library * np.array([1j, -1, -1j, 1])[orders % 4]
    library = library * np.sqrt(2 * orders + 1)
    maximum_kernel_error = float(np.max(np.abs(exact - library)))
    maximum_sigma_error = 0.0
    maximum_green_error = 0.0
    for trial in range(100):
        degree = trial % 32 + 1
        case = make_legendre(trial + 17000, degree=degree)
        result = solve.legendre(case)
        green = exact[:, :degree] @ np.asarray(result["g_legendre"], dtype=np.longdouble)
        auxiliary = exact[:, :degree] @ np.asarray(result["f_legendre"], dtype=np.longdouble)
        sigma = auxiliary / green
        sigma_error = np.sqrt(np.mean(np.abs(decode(result["sigma_iw"]) - sigma)**2))
        sigma_error /= max(1, np.sqrt(np.mean(np.abs(sigma)**2)))
        green_error = np.sqrt(np.mean(np.abs(decode(result["g_iw"]) - green)**2))
        green_error /= max(1, np.sqrt(np.mean(np.abs(green)**2)))
        maximum_sigma_error = max(maximum_sigma_error, float(sigma_error))
        maximum_green_error = max(maximum_green_error, float(green_error))
    report = {
        "decimal_precision": 120,
        "maximum_absolute_kernel_error": maximum_kernel_error,
        "maximum_normalized_green_error": maximum_green_error,
        "maximum_normalized_sigma_error": maximum_sigma_error,
    }
    assert maximum_kernel_error < 1e-14
    assert maximum_green_error < 1e-13
    assert maximum_sigma_error < 1e-11
    text = json.dumps(report, indent=2) + "\n"
    (Path(__file__).resolve().parent / "precision_report.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()

"""Independent bounded parsing and rational arithmetic. No participant imports."""

import json
import re
import stat
from fractions import Fraction
from pathlib import Path


MAX_BYTES = 65536
INTEGER_LIMIT = 10**12
NEGATIVITY_BOUND = Fraction(-1, 10**7)
REQUIRED_KEYS = {"schema_version", "denominator", "coefficients", "x", "vector"}


class InvalidSubmission(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise InvalidSubmission(message)


def _integer_token(token):
    _require(len(token.lstrip("-")) <= 13, "oversized JSON integer")
    return int(token)


def _reject_noninteger(token):
    raise InvalidSubmission("floating numbers and nonfinite constants are forbidden")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def rational(token, label):
    _require(type(token) is str and len(token) <= 28, label + " must be a bounded rational string")
    _require(re.fullmatch(r"-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?", token) is not None, label + " has invalid rational syntax")
    value = Fraction(token)
    _require(str(value) == token, label + " must be a canonical reduced fraction")
    _require(abs(value.numerator) <= INTEGER_LIMIT and value.denominator <= INTEGER_LIMIT, label + " fraction components exceed bounds")
    return value


def load_document(path):
    try:
        metadata = Path(path).stat()
        _require(stat.S_ISREG(metadata.st_mode), "submission must be a regular data file")
        _require(metadata.st_size <= MAX_BYTES, "witness exceeds 65536 bytes")
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        _require(len(raw) <= MAX_BYTES, "witness exceeds 65536 bytes")
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_int=_integer_token,
            parse_float=_reject_noninteger,
            parse_constant=_reject_noninteger,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise InvalidSubmission("unreadable or malformed witness JSON") from error


def matrix_at(coefficients, point):
    coordinate = 2 * point - 1
    basis = [Fraction(1), coordinate]
    for degree in range(2, len(coefficients)):
        basis.append(2 * coordinate * basis[-1] - basis[-2])
    return [
        [sum((matrix[row][column] * value for matrix, value in zip(coefficients, basis)), Fraction(0)) for column in range(4)]
        for row in range(4)
    ]


def commutator_norm_squared(left, right):
    return sum(
        (
            sum((left[row][inner] * right[inner][column] - right[row][inner] * left[inner][column] for inner in range(4)), Fraction(0))
            ** 2
            for row in range(4)
            for column in range(4)
        ),
        Fraction(0),
    )


def check_document(document):
    _require(type(document) is dict and set(document) == REQUIRED_KEYS, "unexpected top-level schema")
    _require(type(document["schema_version"]) is int and document["schema_version"] == 1, "schema_version must be integer 1")
    denominator = document["denominator"]
    _require(type(denominator) is int and 1 <= denominator <= INTEGER_LIMIT, "common denominator must be integer 1..10^12")
    numerators = document["coefficients"]
    _require(type(numerators) is list and 3 <= len(numerators) <= 25, "degree must be 2..24")
    for degree, matrix in enumerate(numerators):
        _require(type(matrix) is list and len(matrix) == 4, "coefficient matrix must have four rows")
        for row in matrix:
            _require(type(row) is list and len(row) == 4, "coefficient row must have four entries")
            _require(all(type(entry) is int and abs(entry) <= denominator for entry in row), "coefficient numerators must be integers bounded by denominator")
        _require(all(matrix[row][column] == matrix[column][row] for row in range(4) for column in range(4)), "coefficients must be exactly symmetric")
        _require(sum(matrix[diagonal][diagonal] for diagonal in range(4)) == (denominator if degree == 0 else 0), "trace must be exactly constant one")
    _require(any(entry != 0 for row in numerators[-1] for entry in row), "highest coefficient matrix must be nonzero")
    _require(all(sum(abs(matrix[row][column]) for matrix in numerators for column in range(4)) <= 4 * denominator for row in range(4)), "Chebyshev row-sum envelope exceeds four")
    point = rational(document["x"], "x")
    _require(Fraction(1, 20) <= point <= Fraction(19, 20), "x must lie in [1/20,19/20]")
    _require(type(document["vector"]) is list and len(document["vector"]) == 4, "vector must have four components")
    vector = [rational(component, "vector component") for component in document["vector"]]
    norm_squared = sum((component**2 for component in vector), Fraction(0))
    _require(all(abs(component) <= 1 for component in vector), "vector components must have magnitude at most one")
    _require(Fraction(1, 4) <= norm_squared <= 4, "vector squared norm must lie in [1/4,4]")
    _require(all(100 * component**2 >= norm_squared for component in vector), "each vector component must carry at least one percent squared weight")
    coefficients = [[[Fraction(entry, denominator) for entry in row] for row in matrix] for matrix in numerators]
    commutator = commutator_norm_squared(matrix_at(coefficients, Fraction(1, 4)), matrix_at(coefficients, Fraction(3, 4)))
    _require(commutator >= Fraction(1, 10**8), "anchor matrices must be genuinely noncommuting")
    value = matrix_at(coefficients, point)
    _require(all(value[diagonal][diagonal] >= Fraction(1, 50) for diagonal in range(4)), "witness diagonal entries must be at least 1/50")
    minors = [value[left][left] * value[right][right] - value[left][right] ** 2 for left in range(4) for right in range(left + 1, 4)]
    _require(min(minors) >= Fraction(1, 10**5), "all six two-by-two principal minors must be at least 10^-5")
    numerator = sum((vector[row] * value[row][column] * vector[column] for row in range(4) for column in range(4)), Fraction(0))
    rayleigh = numerator / norm_squared
    return {
        "coefficients": coefficients,
        "rayleigh": rayleigh,
        "evidence_valid": rayleigh <= NEGATIVITY_BOUND,
        "minimum_principal_minor": min(minors),
        "commutator_squared": commutator,
        "degree": len(coefficients) - 1,
    }


def check_file(path):
    return check_document(load_document(path))
